import json
import uuid

from django.http import StreamingHttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.application.models import Application
from apps.chat.models import ChatMessage
from apps.chat.serializers import ChatRequestSerializer, ChatHistorySerializer
from apps.common.utils import get_request_tenant, fail
from apps.knowledge.search import hybrid_search
from apps.model_provider.llm_adapter import chat_completion_stream


def _build_context(app, query, top_k=3, max_refs=6):
    """检索所有关联知识库，去重后拼接为可引用上下文。"""
    refs = []
    seen = set()
    for kb in app.kbs.all():
        try:
            results = hybrid_search(kb, query, top_k=top_k)
        except Exception:  # noqa
            results = []
        for r in results:
            content = r['paragraph'].content.strip()
            key = content[:60]
            if key in seen:
                continue
            seen.add(key)
            refs.append({
                'content': content,
                'doc_name': r['doc_name'],
                'page_no': r['page_no'],
            })
            if len(refs) >= max_refs:
                break
        if len(refs) >= max_refs:
            break
    return refs


def _format_context(refs):
    if not refs:
        return "（未检索到相关知识库内容）"
    lines = []
    for i, r in enumerate(refs, 1):
        page = f" 第{r['page_no']}页" if r['page_no'] else ""
        lines.append(f"[参考{i}] 来源《{r['doc_name']}》{page}：\n{r['content']}")
    return "\n\n".join(lines)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def chat(request):
    s = ChatRequestSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    data = s.validated_data

    try:
        app = Application.objects.get(id=data['app_id'])
    except Application.DoesNotExist:
        return fail('应用不存在', code=404)
    tenant = get_request_tenant(request)
    if tenant and app.tenant_id != tenant.id:
        return fail('无权限', code=403)

    session_id = data.get('session_id') or str(uuid.uuid4())
    query = data['query']

    # 保存用户消息
    ChatMessage.objects.create(session_id=session_id, app=app,
                               user=request.user, role='user', content=query)

    refs = _build_context(app, query)
    context_text = _format_context(refs)

    messages = [
        {"role": "system", "content": app.system_prompt},
        {"role": "system", "content": f"以下是可供参考的知识库资料：\n{context_text}"},
        {"role": "user", "content": query},
    ]

    def event(payload):
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    def generator():
        answer = []
        try:
            for chunk in chat_completion_stream(
                messages, temperature=app.temperature, max_tokens=app.max_tokens
            ):
                answer.append(chunk)
                yield event({"type": "token", "content": chunk})
            full = "".join(answer)
            ChatMessage.objects.create(session_id=session_id, app=app,
                                       user=request.user, role='assistant',
                                       content=full)
            yield event({
                "type": "done",
                "session_id": session_id,
                "sources": [
                    {"doc_name": r['doc_name'], "page_no": r['page_no']}
                    for r in refs
                ],
            })
        except Exception as e:  # noqa
            yield event({"type": "error", "message": str(e)})

    return StreamingHttpResponse(generator(), content_type='text/event-stream')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def history(request):
    session_id = request.query_params.get('session_id')
    if not session_id:
        return fail('session_id 必填', code=400)
    msgs = ChatMessage.objects.filter(session_id=session_id).order_by('create_time')
    return Response(ChatHistorySerializer(msgs, many=True).data)
