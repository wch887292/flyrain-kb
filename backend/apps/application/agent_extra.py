"""智能体扩展 API：MCP 服务器管理、文件上传、评价优化、分享发布、版本管理。"""
import os
import uuid
import logging
from typing import Dict

from django.http import FileResponse, Http404
from django.utils import timezone
from rest_framework import viewsets, serializers
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser

from apps.common.utils import get_request_tenant, ok, fail
from apps.common.rbac import RoleRequiredMixin, ROLE_ADMIN, ROLE_EDITOR
from apps.application.models import (
    Agent, AgentConversation, AgentMessage, AgentFile, AgentEvaluation, MCPServer, AgentVersion
)
from apps.application.mcp_client import MCPClient
from apps.application.agent_optimizer import evaluate_conversation, apply_optimization
from apps.application.code_interpreter import get_sandbox_status, execute_code

logger = logging.getLogger(__name__)

UPLOAD_DIR = 'uploads/agent_files'
ALLOWED_EXTENSIONS = {'.csv', '.xlsx', '.xls', '.txt', '.json', '.xml', '.md', '.py', '.pdf'}


# ============ MCP 服务器管理 ============

class MCPServerSerializer(serializers.ModelSerializer):
    class Meta:
        model = MCPServer
        fields = ('id', 'name', 'transport', 'url', 'command', 'args', 'env',
                  'headers', 'tools_cache', 'is_active', 'create_time', 'update_time')
        read_only_fields = ('id', 'tools_cache', 'create_time', 'update_time')

    def create(self, validated_data):
        tenant = get_request_tenant(self.context['request'])
        return MCPServer.objects.create(tenant=tenant, **validated_data)


class MCPServerViewSet(RoleRequiredMixin, viewsets.ModelViewSet):
    """MCP 服务器管理"""
    write_roles = (ROLE_ADMIN, ROLE_EDITOR)
    serializer_class = MCPServerSerializer
    pagination_class = None

    def get_queryset(self):
        tenant = get_request_tenant(self.request)
        qs = MCPServer.objects.filter(is_active=True)
        if tenant:
            qs = qs.filter(tenant=tenant)
        return qs.order_by('-create_time')

    def get_serializer_context(self):
        return {'request': self.request}

    @action(detail=True, methods=['post'])
    def refresh_tools(self, request, pk=None):
        """刷新工具列表"""
        server = self.get_object()
        try:
            client = MCPClient(server)
            tools = client.list_tools()
            return ok({'tools': tools, 'count': len(tools)})
        except Exception as e:
            return fail(str(e), code=500)

    @action(detail=True, methods=['post'])
    def test_connection(self, request, pk=None):
        """测试连接"""
        server = self.get_object()
        try:
            client = MCPClient(server)
            success = client.initialize()
            if success:
                tools = client.list_tools()
                return ok({'connected': True, 'tools_count': len(tools)})
            return fail('连接失败', code=500)
        except Exception as e:
            return fail(str(e), code=500)


# ============ 文件上传 ============

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_file(request):
    """上传文件到智能体会话。form: session_id, file"""
    session_id = request.data.get('session_id')
    if not session_id:
        return fail('session_id 必填', code=400)

    try:
        conv = AgentConversation.objects.get(session_id=session_id, user=request.user)
    except AgentConversation.DoesNotExist:
        return fail('会话不存在', code=404)

    if 'file' not in request.FILES:
        return fail('未找到文件', code=400)

    uploaded = request.FILES['file']
    ext = os.path.splitext(uploaded.name)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return fail(f'不支持的文件类型: {ext}，支持: {", ".join(ALLOWED_EXTENSIONS)}', code=400)

    if uploaded.size > 20 * 1024 * 1024:  # 20MB
        return fail('文件大小不能超过 20MB', code=400)

    # 保存文件
    save_dir = os.path.join(UPLOAD_DIR, str(conv.id))
    os.makedirs(save_dir, exist_ok=True)
    safe_name = f"{uuid.uuid4().hex}_{uploaded.name}"
    save_path = os.path.join(save_dir, safe_name)

    with open(save_path, 'wb') as f:
        for chunk in uploaded.chunks():
            f.write(chunk)

    agent_file = AgentFile.objects.create(
        conversation=conv,
        file_name=uploaded.name,
        file_path=save_path,
        file_size=uploaded.size,
        file_type=ext,
        uploader=request.user,
    )

    return ok({
        'id': agent_file.id,
        'file_name': agent_file.file_name,
        'file_size': agent_file.file_size,
        'file_type': agent_file.file_type,
        'message': f'文件已上传，智能体可通过 data/{agent_file.file_name} 访问',
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_files(request):
    """获取会话的文件列表。query: session_id"""
    session_id = request.query_params.get('session_id')
    if not session_id:
        return fail('session_id 必填', code=400)
    try:
        conv = AgentConversation.objects.get(session_id=session_id, user=request.user)
    except AgentConversation.DoesNotExist:
        return fail('会话不存在', code=404)
    files = conv.files.all().order_by('-create_time')
    return ok([{
        'id': f.id, 'file_name': f.file_name, 'file_size': f.file_size,
        'file_type': f.file_type, 'create_time': f.create_time.strftime('%Y-%m-%d %H:%M:%S'),
    } for f in files])


# ============ 评价优化 ============

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def evaluate(request):
    """评价对话并生成优化建议。body: {session_id}"""
    session_id = request.data.get('session_id')
    if not session_id:
        return fail('session_id 必填', code=400)
    try:
        conv = AgentConversation.objects.get(session_id=session_id, user=request.user)
    except AgentConversation.DoesNotExist:
        return fail('会话不存在', code=404)

    evaluation = evaluate_conversation(conv, user_id=request.user.id)
    if not evaluation:
        return fail('评价失败或对话不足', code=500)

    return ok({
        'id': evaluation.id,
        'score': evaluation.score,
        'relevance_score': evaluation.relevance_score,
        'accuracy_score': evaluation.accuracy_score,
        'completeness_score': evaluation.completeness_score,
        'feedback': evaluation.feedback,
        'suggestion': evaluation.suggestion,
        'suggested_prompt': evaluation.suggested_prompt,
        'applied': evaluation.applied,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_evaluations(request):
    """获取智能体的评价列表。query: agent_id"""
    agent_id = request.query_params.get('agent_id')
    if not agent_id:
        return fail('agent_id 必填', code=400)
    evals = AgentEvaluation.objects.filter(agent_id=agent_id).order_by('-create_time')[:50]
    return ok([{
        'id': e.id, 'score': e.score, 'feedback': e.feedback,
        'suggestion': e.suggestion, 'applied': e.applied,
        'create_time': e.create_time.strftime('%Y-%m-%d %H:%M:%S'),
    } for e in evals])


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def apply_evaluation(request):
    """应用优化建议。body: {evaluation_id}"""
    eval_id = request.data.get('evaluation_id')
    if not eval_id:
        return fail('evaluation_id 必填', code=400)
    try:
        evaluation = AgentEvaluation.objects.get(id=eval_id, agent__tenant=get_request_tenant(request))
    except AgentEvaluation.DoesNotExist:
        return fail('评价不存在', code=404)

    success = apply_optimization(evaluation)
    if success:
        return ok({'message': '已应用优化建议，系统提示词已更新'})
    return fail('应用失败（无建议或已应用）', code=400)


# ============ 分享发布 ============

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def share_agent(request):
    """分享智能体，生成分享码。body: {agent_id, is_public?, config?}"""
    agent_id = request.data.get('agent_id')
    is_public = request.data.get('is_public', False)
    config = request.data.get('config', {})

    if not agent_id:
        return fail('agent_id 必填', code=400)
    try:
        agent = Agent.objects.get(id=agent_id, tenant=get_request_tenant(request))
    except Agent.DoesNotExist:
        return fail('智能体不存在', code=404)

    if not agent.share_code:
        agent.share_code = uuid.uuid4().hex[:12]
    agent.is_public = is_public
    agent.share_config = config
    agent.save(update_fields=['share_code', 'is_public', 'share_config', 'update_time'])

    return ok({
        'share_code': agent.share_code,
        'is_public': agent.is_public,
        'share_url': f'/agent/share/{agent.share_code}',
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def get_shared_agent(request, share_code):
    """获取分享的智能体信息（公开访问）。"""
    try:
        agent = Agent.objects.get(share_code=share_code, is_active=True)
    except Agent.DoesNotExist:
        return fail('分享不存在或已失效', code=404)

    if not agent.is_public and not request.user.is_authenticated:
        return fail('需要登录', code=401)

    return ok({
        'id': agent.id,
        'name': agent.name,
        'avatar': agent.avatar,
        'description': agent.description,
        'role': agent.role,
        'opening_message': agent.opening_message,
        'suggested_questions': agent.suggested_questions,
        'share_code': agent.share_code,
    })


# ============ 智能体版本发布与回滚 ============

def _snapshot_agent_config(agent: Agent) -> Dict:
    """创建智能体配置快照。"""
    return {
        'name': agent.name,
        'description': agent.description,
        'role': agent.role,
        'system_prompt': agent.system_prompt,
        'temperature': agent.temperature,
        'max_tokens': agent.max_tokens,
        'max_iterations': agent.max_iterations,
        'opening_message': agent.opening_message,
        'suggested_questions': agent.suggested_questions,
        'enable_reasoning': agent.enable_reasoning,
        'enable_code_interpreter': agent.enable_code_interpreter,
        'enable_auto_optimize': agent.enable_auto_optimize,
        'kb_ids': list(agent.kbs.values_list('id', flat=True)),
        'tool_ids': list(agent.tools.values_list('id', flat=True)),
        'mcp_server_ids': list(agent.mcp_servers.values_list('id', flat=True)),
        'sub_agent_ids': list(agent.sub_agents.values_list('id', flat=True)),
    }


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def publish_version(request):
    """发布智能体版本。body: {agent_id, version, name?, description?}"""
    agent_id = request.data.get('agent_id')
    version = request.data.get('version', '').strip()
    name = request.data.get('name', '')
    description = request.data.get('description', '')

    if not agent_id or not version:
        return fail('agent_id 和 version 必填', code=400)

    try:
        agent = Agent.objects.get(id=agent_id, tenant=get_request_tenant(request))
    except Agent.DoesNotExist:
        return fail('智能体不存在', code=404)

    # 检查版本号是否已存在
    if AgentVersion.objects.filter(agent=agent, version=version).exists():
        return fail(f'版本号 {version} 已存在', code=400)

    # 取消其他版本的当前标记
    AgentVersion.objects.filter(agent=agent).update(is_current=False)

    # 创建新版本
    agent_version = AgentVersion.objects.create(
        agent=agent,
        version=version,
        name=name or f'v{version}',
        description=description,
        config_snapshot=_snapshot_agent_config(agent),
        is_current=True,
        is_published=True,
        created_by=request.user,
    )

    return ok({
        'id': agent_version.id,
        'version': agent_version.version,
        'name': agent_version.name,
        'message': f'版本 v{version} 已发布',
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_versions(request):
    """获取智能体版本列表。query: agent_id"""
    agent_id = request.query_params.get('agent_id')
    if not agent_id:
        return fail('agent_id 必填', code=400)
    versions = AgentVersion.objects.filter(agent_id=agent_id).order_by('-create_time')
    return ok([{
        'id': v.id, 'version': v.version, 'name': v.name, 'description': v.description,
        'is_current': v.is_current, 'is_published': v.is_published,
        'created_by': v.created_by.username if v.created_by else '',
        'create_time': v.create_time.strftime('%Y-%m-%d %H:%M:%S'),
    } for v in versions])


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def rollback_version(request):
    """回滚到指定版本。body: {version_id}"""
    version_id = request.data.get('version_id')
    if not version_id:
        return fail('version_id 必填', code=400)

    try:
        version = AgentVersion.objects.get(id=version_id, agent__tenant=get_request_tenant(request))
    except AgentVersion.DoesNotExist:
        return fail('版本不存在', code=404)

    agent = version.agent
    config = version.config_snapshot

    # 恢复配置
    agent.name = config.get('name', agent.name)
    agent.description = config.get('description', agent.description)
    agent.role = config.get('role', agent.role)
    agent.system_prompt = config.get('system_prompt', agent.system_prompt)
    agent.temperature = config.get('temperature', agent.temperature)
    agent.max_tokens = config.get('max_tokens', agent.max_tokens)
    agent.max_iterations = config.get('max_iterations', agent.max_iterations)
    agent.opening_message = config.get('opening_message', agent.opening_message)
    agent.suggested_questions = config.get('suggested_questions', agent.suggested_questions)
    agent.enable_reasoning = config.get('enable_reasoning', agent.enable_reasoning)
    agent.enable_code_interpreter = config.get('enable_code_interpreter', agent.enable_code_interpreter)
    agent.enable_auto_optimize = config.get('enable_auto_optimize', agent.enable_auto_optimize)
    agent.save()

    # 恢复关联
    if 'kb_ids' in config:
        agent.kbs.set(config['kb_ids'])
    if 'tool_ids' in config:
        agent.tools.set(config['tool_ids'])
    if 'mcp_server_ids' in config:
        agent.mcp_servers.set(config['mcp_server_ids'])
    if 'sub_agent_ids' in config:
        agent.sub_agents.set(config['sub_agent_ids'])

    # 更新当前版本标记
    AgentVersion.objects.filter(agent=agent).update(is_current=False)
    version.is_current = True
    version.save(update_fields=['is_current'])

    return ok({
        'message': f'已回滚到版本 v{version.version}',
        'version': version.version,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def compare_versions(request):
    """对比两个版本的配置差异。query: version_id_1, version_id_2"""
    v1_id = request.query_params.get('version_id_1')
    v2_id = request.query_params.get('version_id_2')
    if not v1_id or not v2_id:
        return fail('version_id_1 和 version_id_2 必填', code=400)

    try:
        v1 = AgentVersion.objects.get(id=v1_id)
        v2 = AgentVersion.objects.get(id=v2_id)
    except AgentVersion.DoesNotExist:
        return fail('版本不存在', code=404)

    c1 = v1.config_snapshot
    c2 = v2.config_snapshot
    diffs = []

    all_keys = set(list(c1.keys()) + list(c2.keys()))
    for key in sorted(all_keys):
        val1 = c1.get(key)
        val2 = c2.get(key)
        if val1 != val2:
            diffs.append({
                'field': key,
                'version_1': str(val1)[:200] if val1 else '',
                'version_2': str(val2)[:200] if val2 else '',
            })

    return ok({
        'version_1': {'id': v1.id, 'version': v1.version, 'name': v1.name},
        'version_2': {'id': v2.id, 'version': v2.version, 'name': v2.name},
        'diffs': diffs,
        'diff_count': len(diffs),
    })


# ============ 沙箱状态 ============

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def sandbox_status(request):
    """获取代码执行沙箱状态。"""
    return ok(get_sandbox_status())
