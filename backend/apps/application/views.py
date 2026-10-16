import re
import time
import json
import logging
import requests as http_requests

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.application.models import Application, Workflow, WorkflowStep, WorkflowExecution, Plugin
from apps.application.serializers import (
    ApplicationSerializer, WorkflowSerializer, WorkflowStepSerializer, WorkflowExecutionSerializer,
    PluginSerializer
)
from apps.common.utils import get_request_tenant, ok, fail
from apps.common.rbac import RoleRequiredMixin, ROLE_ADMIN, ROLE_EDITOR
from apps.model_provider.llm_adapter import chat_completion

logger = logging.getLogger(__name__)


class ApplicationViewSet(RoleRequiredMixin, viewsets.ModelViewSet):
    write_roles = (ROLE_ADMIN, ROLE_EDITOR)
    serializer_class = ApplicationSerializer

    def get_queryset(self):
        tenant = get_request_tenant(self.request)
        qs = Application.objects.all()
        if tenant:
            qs = qs.filter(tenant=tenant)
        return qs.order_by('-create_time')

    def get_serializer_context(self):
        return {'request': self.request}


class PluginViewSet(RoleRequiredMixin, viewsets.ModelViewSet):
    """插件管理：HTTP 插件，可在工作流步骤中调用。"""
    write_roles = (ROLE_ADMIN, ROLE_EDITOR)
    serializer_class = PluginSerializer
    pagination_class = None

    def get_queryset(self):
        tenant = get_request_tenant(self.request)
        qs = Plugin.objects.all()
        if tenant:
            qs = qs.filter(tenant=tenant)
        return qs.order_by('-create_time')

    def perform_create(self, serializer):
        self._check_write()
        tenant = get_request_tenant(self.request)
        serializer.save(tenant=tenant)

    @action(detail=True, methods=['post'])
    def test(self, request, pk=None):
        """测试插件调用。body: {input_text}"""
        plugin = self.get_object()
        input_text = request.data.get('input_text', 'test')
        try:
            result = _execute_plugin(plugin, input_text, {})
            return ok({'result': result[:500]}, message='测试成功')
        except Exception as e:
            logger.warning("插件测试失败: plugin=%s, error=%s", plugin.name, e, exc_info=True)
            return fail(f'测试失败: {str(e)}', code=400)


def _execute_plugin(plugin, input_text, step_outputs):
    """执行 HTTP 插件。

    config 结构：{url, method, headers:{}, body_template, timeout}
    body_template 中可用 {{input}} 引用输入，{{step_N.output}} 引用步骤输出。
    """
    config = plugin.config or {}
    url = config.get('url', '')
    method = (config.get('method', 'POST') or 'POST').upper()
    headers = config.get('headers', {}) or {}
    body_template = config.get('body_template', '{{input}}')
    timeout = config.get('timeout', 30)

    if not url:
        raise ValueError('插件未配置 URL')

    # 变量替换
    body = body_template.replace('{{input}}', input_text)
    for i, prev in enumerate(step_outputs, start=1):
        body = body.replace(f'{{{{step_{i}.output}}}}', prev.get('output', ''))

    # 尝试解析为 JSON
    try:
        json_body = json.loads(body)
    except (json.JSONDecodeError, TypeError):
        json_body = body

    if method == 'GET':
        resp = http_requests.get(url, headers=headers, params={'input': input_text}, timeout=timeout)
    else:
        resp = http_requests.request(method, url, headers=headers, json=json_body, timeout=timeout)

    resp.raise_for_status()
    # 尝试解析 JSON 响应，否则返回文本
    try:
        data = resp.json()
        return json.dumps(data, ensure_ascii=False, indent=2)
    except Exception:
        return resp.text


class WorkflowViewSet(RoleRequiredMixin, viewsets.ModelViewSet):
    write_roles = (ROLE_ADMIN, ROLE_EDITOR)
    serializer_class = WorkflowSerializer

    def get_queryset(self):
        tenant = get_request_tenant(self.request)
        qs = Workflow.objects.all()
        if tenant:
            qs = qs.filter(tenant=tenant)
        return qs.order_by('-create_time')

    def get_serializer_context(self):
        return {'request': self.request}

    @action(detail=True, methods=['get'])
    def steps(self, request, pk=None):
        wf = self.get_object()
        return Response(WorkflowStepSerializer(wf.steps.all(), many=True).data)

    @action(detail=True, methods=['post'])
    def add_step(self, request, pk=None):
        self._check_write()
        wf = self.get_object()
        data = request.data.copy()
        if 'order' not in data:
            data['order'] = wf.steps.count() + 1
        serializer = WorkflowStepSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        step = serializer.save(workflow=wf)
        return Response(WorkflowStepSerializer(step).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def reorder_steps(self, request, pk=None):
        self._check_write()
        wf = self.get_object()
        step_ids = request.data.get('step_ids', [])
        if not isinstance(step_ids, list) or not step_ids:
            return fail('step_ids 必须是非空数组', code=400)
        for i, sid in enumerate(step_ids, start=1):
            WorkflowStep.objects.filter(pk=sid, workflow=wf).update(order=i)
        return ok({'reordered': len(step_ids)}, message='排序完成')

    @action(detail=True, methods=['delete'])
    def delete_step(self, request, pk=None):
        """删除步骤。body: {step_id}"""
        self._check_write()
        wf = self.get_object()
        step_id = request.data.get('step_id')
        if not step_id:
            return fail('step_id 必填', code=400)
        deleted, _ = WorkflowStep.objects.filter(pk=step_id, workflow=wf).delete()
        if not deleted:
            return fail('步骤不存在', code=404)
        return ok({}, message='已删除')

    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """执行工作流：串行执行所有步骤，支持 LLM 调用和插件调用。"""
        wf = self.get_object()
        input_text = request.data.get('input_text', '')
        if not input_text:
            return fail('input_text 必填', code=400)
        steps = wf.steps.all().order_by('order')
        if not steps.exists():
            return fail('工作流没有步骤', code=400)

        execution = WorkflowExecution.objects.create(
            workflow=wf, user=request.user, input_text=input_text, status='running'
        )
        start_time = time.time()
        step_outputs = []
        current_output = ''

        try:
            for step in steps:
                if step.step_type == 'plugin' and step.plugin:
                    # 插件调用
                    logger.info("工作流插件执行: wf=%s, step=%s, plugin=%s",
                                wf.name, step.name, step.plugin.name)
                    output = _execute_plugin(step.plugin, input_text, step_outputs)
                else:
                    # LLM 调用
                    prompt = step.prompt
                    prompt = prompt.replace('{{input}}', input_text)
                    for i, prev in enumerate(step_outputs, start=1):
                        prompt = prompt.replace(f'{{{{step_{i}.output}}}}', prev.get('output', ''))
                    logger.info("工作流执行: wf=%s, step=%s, prompt_len=%s",
                                wf.name, step.name, len(prompt))
                    output = chat_completion(
                        [{"role": "user", "content": prompt}],
                        temperature=step.temperature, max_tokens=step.max_tokens,
                        user_id=request.user.id,
                    )
                current_output = output or ''
                step_outputs.append({
                    'step_order': step.order,
                    'step_name': step.name,
                    'step_type': step.step_type,
                    'output': current_output,
                })

            execution.output_text = current_output
            execution.step_outputs = step_outputs
            execution.status = 'success'
        except Exception as e:
            execution.status = 'failed'
            execution.error_msg = str(e)[:1000]
            execution.step_outputs = step_outputs
            logger.error("工作流执行失败: wf=%s, error=%s", wf.name, e, exc_info=True)
        finally:
            execution.duration_ms = round((time.time() - start_time) * 1000, 1)
            execution.save()

        return Response(WorkflowExecutionSerializer(execution).data,
                        status=status.HTTP_201_CREATED if execution.status == 'success'
                        else status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'])
    def executions(self, request, pk=None):
        wf = self.get_object()
        execs = wf.executions.all()[:50]
        return Response(WorkflowExecutionSerializer(execs, many=True).data)
