"""对外 API v1：使用 API Key 认证，提供对话和检索接口。

认证方式：
- Header: Authorization: Bearer <api_key>
- 或 Header: X-API-Key: <api_key>
"""
import json
import uuid
import logging
from functools import wraps

from django.http import StreamingHttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_http_methods

from apps.users.models import ApiKey
from apps.application.models import Application
from apps.knowledge.models import KnowledgeBase
from apps.knowledge.search import hybrid_search
from apps.model_provider.llm_adapter import chat_completion_stream

logger = logging.getLogger(__name__)


def api_key_auth(view_func):
    """API Key 认证装饰器。"""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        # 从 Header 提取 API Key
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        api_key_str = ''
        if auth_header.startswith('Bearer '):
            api_key_str = auth_header[7:]
        if not api_key_str:
            api_key_str = request.META.get('HTTP_X_API_KEY', '')

        if not api_key_str:
            return JsonResponse({'error': '缺少 API Key', 'code': 401}, status=401)

        try:
            api_key = ApiKey.objects.get(key=api_key_str, status='active')
        except ApiKey.DoesNotExist:
            return JsonResponse({'error': 'API Key 无效或已禁用', 'code': 401}, status=401)

        # 检查过期
        if api_key.expires_at and api_key.expires_at < timezone.now():
            return JsonResponse({'error': 'API Key 已过期', 'code': 401}, status=401)

        # 更新使用统计
        api_key.call_count += 1
        api_key.last_used_at = timezone.now()
        api_key.save(update_fields=['call_count', 'last_used_at'])

        request.api_key = api_key
        request.api_user = api_key.user
        return view_func(request, *args, **kwargs)
    return _wrapped


@csrf_exempt
@require_POST
@api_key_auth
def chat_api(request):
    """对外对话接口（SSE 流式）。
    body: {app_id, query, session_id?}
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': '无效的 JSON', 'code': 400}, status=400)

    app_id = data.get('app_id')
    query = data.get('query', '').strip()
    if not app_id or not query:
        return JsonResponse({'error': 'app_id 和 query 必填', 'code': 400}, status=400)

    try:
        app = Application.objects.get(id=app_id, tenant=request.api_key.tenant, is_active=True)
    except Application.DoesNotExist:
        return JsonResponse({'error': '应用不存在或未启用', 'code': 404}, status=404)

    session_id = data.get('session_id') or str(uuid.uuid4())

    # 检索上下文
    refs = []
    seen = set()
    for kb in app.kbs.all():
        try:
            results = hybrid_search(kb, query, top_k=3, vector_weight=getattr(app, 'vector_weight', 0.7))
        except Exception:
            results = []
        for r in results:
            content = r['paragraph'].content.strip()
            key = content[:60]
            if key in seen:
                continue
            seen.add(key)
            refs.append({'content': content, 'doc_name': r['doc_name'], 'page_no': r['page_no']})
            if len(refs) >= 6:
                break
        if len(refs) >= 6:
            break

    context_text = "\n\n".join([
        f"[参考{i+1}] 来源《{r['doc_name']}》：\n{r['content']}" for i, r in enumerate(refs)
    ]) or "（未检索到相关内容）"

    messages = [
        {"role": "system", "content": app.system_prompt},
        {"role": "system", "content": f"参考资料：\n{context_text}"},
        {"role": "user", "content": query},
    ]

    def event(payload):
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    def generator():
        answer = []
        try:
            for chunk in chat_completion_stream(
                messages, temperature=app.temperature, max_tokens=app.max_tokens,
                user_id=request.api_user.id, app_id=app.id
            ):
                answer.append(chunk)
                yield event({"type": "token", "content": chunk})
            yield event({
                "type": "done", "session_id": session_id,
                "sources": [{"doc_name": r['doc_name'], "page_no": r['page_no']} for r in refs],
            })
        except Exception as e:
            yield event({"type": "error", "message": str(e)})

    return StreamingHttpResponse(generator(), content_type='text/event-stream')


@csrf_exempt
@require_POST
@api_key_auth
def search_api(request):
    """对外检索接口。
    body: {kb_id, query, top_k?, vector_weight?}
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': '无效的 JSON', 'code': 400}, status=400)

    kb_id = data.get('kb_id')
    query = data.get('query', '').strip()
    top_k = int(data.get('top_k', 5))
    vector_weight = float(data.get('vector_weight', 0.7))

    if not kb_id or not query:
        return JsonResponse({'error': 'kb_id 和 query 必填', 'code': 400}, status=400)

    try:
        kb = KnowledgeBase.objects.get(id=kb_id, tenant=request.api_key.tenant)
    except KnowledgeBase.DoesNotExist:
        return JsonResponse({'error': '知识库不存在', 'code': 404}, status=404)

    results = hybrid_search(kb, query, top_k=top_k, vector_weight=vector_weight)
    return JsonResponse({
        'results': [{
            'content': r['paragraph'].content,
            'score': round(r['score'], 4),
            'doc_name': r['doc_name'],
            'page_no': r['page_no'],
        } for r in results]
    })
