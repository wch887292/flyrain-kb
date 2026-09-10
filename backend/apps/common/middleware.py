"""审计中间件：记录用户的关键写操作到 AuditLog。"""
import json
import logging

from apps.common.models import AuditLog

logger = logging.getLogger(__name__)

# 不需要审计的路径前缀（SSE 流式、静态文件、API 文档等）
SKIP_PATH_PREFIXES = (
    '/api/chat/',       # SSE 流式对话，单独记录
    '/static/',
    '/media/',
    '/api/schema/',
    '/api/docs/',
    '/api/redoc/',
    '/admin/',
)

# 需要审计的 HTTP 方法
AUDIT_METHODS = ('POST', 'PUT', 'PATCH', 'DELETE')


class AuditMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        # 响应返回后异步记录审计日志（不阻塞响应）
        try:
            self._log(request, response)
        except Exception as e:
            logger.warning("审计日志记录失败: %s", e)
        return response

    def _log(self, request, response):
        if request.method not in AUDIT_METHODS:
            return
        path = request.path
        if any(path.startswith(p) for p in SKIP_PATH_PREFIXES):
            return

        user = getattr(request, 'user', None)
        if not (user and getattr(user, 'is_authenticated', False)):
            return  # 未认证请求不记录（登录接口单独处理）

        # 从路径推断资源类型和操作
        resource_type, action = self._infer_resource(path, request.method)

        # 尝试从响应中提取资源 ID（创建操作返回的 data 中可能有 id）
        resource_id = None
        try:
            if hasattr(response, 'data') and isinstance(response.data, dict):
                data = response.data.get('data') or response.data
                if isinstance(data, dict):
                    resource_id = data.get('id')
        except Exception:
            pass

        # 从 URL 路径中提取资源 ID（如 /api/knowledge/bases/123/）
        if not resource_id:
            resource_id = self._extract_id_from_path(path)

        AuditLog.objects.create(
            user=user,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip=self._get_client_ip(request),
            path=path[:255],
            method=request.method,
            status_code=response.status_code,
            detail=self._build_detail(request),
        )

    def _infer_resource(self, path: str, method: str) -> tuple:
        """从 URL 路径推断资源类型和操作类型"""
        action_map = {'POST': 'create', 'PUT': 'update', 'PATCH': 'update', 'DELETE': 'delete'}
        action = action_map.get(method, 'other')

        if '/knowledge/bases/' in path:
            if '/upload/' in path:
                action = 'upload'
            return 'knowledge_base', action
        if '/knowledge/documents/' in path:
            if '/reparse/' in path:
                action = 'reparse'
            return 'document', action
        if '/application/apps/' in path:
            return 'application', action
        if '/users/' in path and '/register/' not in path and '/login/' not in path:
            return 'user', action
        if '/model/providers/' in path:
            return 'model_provider', action
        return 'other', action

    def _extract_id_from_path(self, path: str):
        """从 URL 路径中提取数字 ID"""
        parts = [p for p in path.split('/') if p.isdigit()]
        return int(parts[-1]) if parts else None

    def _get_client_ip(self, request):
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded:
            return x_forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')

    def _build_detail(self, request) -> str:
        """构建操作详情（请求体摘要，避免记录敏感信息如密码）"""
        try:
            if request.method in ('POST', 'PUT', 'PATCH'):
                body = request.body[:1000].decode('utf-8', errors='replace')
                if body:
                    data = json.loads(body)
                    # 脱敏：移除密码、密钥等敏感字段
                    for key in ('password', 'api_key', 'secret', 'token'):
                        if key in data:
                            data[key] = '***'
                    return json.dumps(data, ensure_ascii=False)[:500]
        except Exception:
            pass
        return ''
