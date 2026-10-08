"""智能体 API：CRUD + 对话 + 会话管理。"""
import json
import uuid
import logging

from django.http import StreamingHttpResponse
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import serializers

from apps.common.utils import get_request_tenant, ok, fail
from apps.common.rbac import RoleRequiredMixin, ROLE_ADMIN, ROLE_EDITOR
from apps.application.models import Agent, AgentConversation, AgentMessage, Plugin
from apps.knowledge.models import KnowledgeBase
from apps.application.agent_engine import run_agent

logger = logging.getLogger(__name__)


class AgentSerializer(serializers.ModelSerializer):
    kb_ids = serializers.PrimaryKeyRelatedField(
        many=True, write_only=True, required=False, source='kbs',
        queryset=KnowledgeBase.objects.all()
    )
    tool_ids = serializers.PrimaryKeyRelatedField(
        many=True, write_only=True, required=False, source='tools',
        queryset=Plugin.objects.all()
    )
    kb_names = serializers.SerializerMethodField()
    tool_names = serializers.SerializerMethodField()

    class Meta:
        model = Agent
        fields = ('id', 'name', 'avatar', 'description', 'role', 'system_prompt',
                  'kb_ids', 'kb_names', 'tool_ids', 'tool_names',
                  'temperature', 'max_tokens', 'max_iterations',
                  'opening_message', 'suggested_questions', 'enable_reasoning',
                  'enable_code_interpreter', 'enable_fhcode',
                  'is_active', 'create_time', 'update_time')
        read_only_fields = ('id', 'kb_names', 'tool_names', 'create_time', 'update_time')

    def get_kb_names(self, obj):
        return [kb.name for kb in obj.kbs.all()]

    def get_tool_names(self, obj):
        return [t.name for t in obj.tools.all()]

    def create(self, validated_data):
        kbs = validated_data.pop('kbs', [])
        tools = validated_data.pop('tools', [])
        tenant = get_request_tenant(self.context['request'])
        agent = Agent.objects.create(tenant=tenant, **validated_data)
        if kbs:
            agent.kbs.set(kbs)
        if tools:
            agent.tools.set(tools)
        return agent

    def update(self, instance, validated_data):
        kbs = validated_data.pop('kbs', None)
        tools = validated_data.pop('tools', None)
        for k, v in validated_data.items():
            setattr(instance, k, v)
        instance.save()
        if kbs is not None:
            instance.kbs.set(kbs)
        if tools is not None:
            instance.tools.set(tools)
        return instance


class AgentViewSet(RoleRequiredMixin, viewsets.ModelViewSet):
    """智能体管理：CRUD。"""
    write_roles = (ROLE_ADMIN, ROLE_EDITOR)
    serializer_class = AgentSerializer
    pagination_class = None

    def get_queryset(self):
        tenant = get_request_tenant(self.request)
        qs = Agent.objects.filter(is_active=True)
        if tenant:
            qs = qs.filter(tenant=tenant)
        return qs.order_by('-create_time')

    def get_serializer_context(self):
        return {'request': self.request}


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def agent_conversations(request):
    """智能体会话列表。query: agent_id（可选）"""
    agent_id = request.query_params.get('agent_id')
    qs = AgentConversation.objects.filter(user=request.user)
    if agent_id:
        qs = qs.filter(agent_id=agent_id)
    convs = qs.order_by('-update_time')[:50]
    return ok([{
        'id': c.id, 'session_id': c.session_id, 'agent_id': c.agent_id,
        'agent_name': c.agent.name, 'title': c.title,
        'create_time': c.create_time.strftime('%Y-%m-%d %H:%M:%S'),
        'update_time': c.update_time.strftime('%Y-%m-%d %H:%M:%S'),
    } for c in convs])


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def agent_history(request):
    """智能体对话历史。query: session_id"""
    session_id = request.query_params.get('session_id')
    if not session_id:
        return fail('session_id 必填', code=400)
    try:
        conv = AgentConversation.objects.get(session_id=session_id, user=request.user)
    except AgentConversation.DoesNotExist:
        return fail('会话不存在', code=404)
    msgs = conv.messages.all().order_by('create_time')
    return ok([{
        'id': m.id, 'role': m.role, 'content': m.content,
        'reasoning': m.reasoning, 'tool_calls': m.tool_calls,
        'tool_name': m.tool_name, 'images': m.images,
        'create_time': m.create_time.strftime('%Y-%m-%d %H:%M:%S'),
    } for m in msgs])


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def agent_chat(request):
    """智能体对话（SSE 流式）。
    body: {agent_id, query, session_id?}
    """
    agent_id = request.data.get('agent_id')
    query = request.data.get('query', '').strip()
    session_id = request.data.get('session_id') or str(uuid.uuid4())

    if not agent_id or not query:
        return fail('agent_id 和 query 必填', code=400)

    try:
        agent = Agent.objects.get(id=agent_id, is_active=True)
    except Agent.DoesNotExist:
        return fail('智能体不存在或未启用', code=404)

    # 获取或创建会话
    conv, created = AgentConversation.objects.get_or_create(
        session_id=session_id,
        defaults={'agent': agent, 'user': request.user, 'title': query[:30]}
    )
    if not created and conv.user_id != request.user.id:
        return fail('无权限', code=403)

    # 保存用户消息
    AgentMessage.objects.create(conversation=conv, role='user', content=query)

    # 构建历史消息
    history_msgs = []
    for m in conv.messages.all().order_by('create_time'):
        if m.role == 'user':
            history_msgs.append({"role": "user", "content": m.content})
        elif m.role == 'assistant':
            history_msgs.append({"role": "assistant", "content": m.content})
        elif m.role == 'tool':
            history_msgs.append({"role": "user", "content": f"工具返回：{m.content}"})

    def event(payload):
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    def generator():
        full_answer = ""
        reasoning_text = ""
        tool_calls = []

        try:
            for evt in run_agent(agent, query, history=history_msgs, user_id=request.user.id):
                if evt['type'] == 'reasoning':
                    reasoning_text += evt.get('content', '')
                    yield event(evt)
                elif evt['type'] == 'tool_call':
                    tool_calls.append({'tool': evt['tool'], 'input': evt['input']})
                    yield event(evt)
                elif evt['type'] == 'tool_result':
                    # 保存工具结果消息
                    AgentMessage.objects.create(
                        conversation=conv, role='tool',
                        content=evt.get('result', '')[:2000],
                        tool_name=evt.get('tool', ''),
                        images=evt.get('images', [])[:5],
                    )
                    yield event(evt)
                elif evt['type'] == 'token':
                    full_answer += evt.get('content', '')
                    yield event(evt)
                elif evt['type'] == 'done':
                    full_answer = evt.get('answer', full_answer)
                    # 保存助手消息
                    AgentMessage.objects.create(
                        conversation=conv, role='assistant',
                        content=full_answer, reasoning=reasoning_text,
                        tool_calls=tool_calls
                    )
                    # 更新会话标题和时间
                    if created or conv.title == '新对话':
                        conv.title = query[:30]
                    conv.save(update_fields=['title', 'update_time'])
                    yield event({**evt, 'session_id': session_id})
                    return
                elif evt['type'] == 'error':
                    yield event(evt)
                    return
        except Exception as e:
            logger.error("智能体对话失败: agent=%s, error=%s", agent_id, e, exc_info=True)
            yield event({"type": "error", "message": str(e)})

    return StreamingHttpResponse(generator(), content_type='text/event-stream')
