"""RBAC：基于用户角色的写操作权限控制。

角色三档：
- admin  ：管理员，拥有全部权限（含模型配置、用户管理）
- editor ：知识库维护，可管理知识库 / 文档 / AI 应用，不可改模型与用户
- user   ：普通用户，仅可查看与对话，不可写资源

用法：
    class XxxViewSet(RoleRequiredMixin, viewsets.ModelViewSet):
        write_roles = (ROLE_ADMIN, ROLE_EDITOR)   # 该类写操作允许的角色
        # 若自带有 perform_create 等，请在方法首行调用 self._check_role()
"""
from rest_framework.exceptions import PermissionDenied

ROLE_ADMIN = 'admin'
ROLE_EDITOR = 'editor'
ROLE_USER = 'user'

# 角色中文名（用于前端展示）
ROLE_LABELS = {
    ROLE_ADMIN: '管理员',
    ROLE_EDITOR: '知识库维护',
    ROLE_USER: '普通用户',
}

# 各资源写操作允许的角色
WRITE_ROLES = {
    'knowledge': [ROLE_ADMIN, ROLE_EDITOR],
    'application': [ROLE_ADMIN, ROLE_EDITOR],
    'model': [ROLE_ADMIN],
    'user': [ROLE_ADMIN],
}


class RoleRequiredMixin:
    """在 ViewSet 上声明 write_roles / read_roles，对写/读操作做角色校验。

    - write_roles: 允许写（create/update/destroy）的角色
    - read_roles : 允许读（list/retrieve）的角色；None 表示不限制（任何已登录用户可读）
      默认 None 是为了向后兼容：现有知识库/应用 ViewSet 仅限制写，读对所有登录用户开放。
    """
    write_roles = (ROLE_ADMIN,)
    read_roles = None

    def _check_role(self, roles):
        user = getattr(self, 'request', None) and self.request.user
        if not (user and getattr(user, 'is_authenticated', False)):
            raise PermissionDenied('未认证，无法执行该操作')
        if user.role not in roles:
            allowed = ','.join(roles)
            raise PermissionDenied(f'无权限：该操作仅限 {allowed} 角色')

    def _check_write(self):
        self._check_role(self.write_roles)

    def _check_read(self):
        if self.read_roles is not None:
            self._check_role(self.read_roles)

    def list(self, request, *args, **kwargs):
        self._check_read()
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        self._check_read()
        return super().retrieve(request, *args, **kwargs)

    def perform_create(self, serializer):
        self._check_write()
        super().perform_create(serializer)

    def perform_update(self, serializer):
        self._check_write()
        super().perform_update(serializer)

    def perform_destroy(self, instance):
        self._check_write()
        super().perform_destroy(instance)
