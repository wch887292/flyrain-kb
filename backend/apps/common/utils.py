from rest_framework.response import Response
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    """统一异常结构：{code, message, data}"""
    response = exception_handler(exc, context)
    if response is not None:
        message = '请求处理失败'
        if isinstance(response.data, dict):
            for key in ('detail', 'non_field_errors', 'msg'):
                if key in response.data:
                    message = response.data[key]
                    if isinstance(message, list):
                        message = message[0]
                    break
            # 扁平化字段错误
            if message == '请求处理失败':
                parts = []
                for k, v in response.data.items():
                    val = v[0] if isinstance(v, list) else v
                    parts.append(f'{k}: {val}')
                if parts:
                    message = '; '.join(parts)
        return Response(
            {'code': response.status_code, 'message': str(message), 'data': None},
            status=response.status_code
        )
    return Response(
        {'code': 500, 'message': '服务器内部错误', 'data': None}, status=500
    )


def ok(data=None, message='ok'):
    return Response({'code': 0, 'message': message, 'data': data})


def fail(message='error', code=400, data=None):
    return Response({'code': code, 'message': message, 'data': data}, status=code)


def get_request_tenant(request):
    """从当前登录用户获取所属租户"""
    user = getattr(request, 'user', None)
    if user and getattr(user, 'tenant', None):
        return user.tenant
    return None
