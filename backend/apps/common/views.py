from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.models import AuditLog
from apps.common.serializers import AuditLogSerializer
from apps.common.rbac import RoleRequiredMixin, ROLE_ADMIN
from apps.common.utils import ok


class AuditLogViewSet(RoleRequiredMixin, viewsets.ReadOnlyModelViewSet):
    """审计日志查询（仅 admin）。支持按 action/resource_type/user 过滤。"""
    queryset = AuditLog.objects.select_related('user').all()
    serializer_class = AuditLogSerializer
    read_roles = (ROLE_ADMIN,)
    write_roles = (ROLE_ADMIN,)

    def get_queryset(self):
        qs = super().get_queryset()
        action = self.request.query_params.get('action')
        resource_type = self.request.query_params.get('resource_type')
        user_id = self.request.query_params.get('user_id')
        if action:
            qs = qs.filter(action=action)
        if resource_type:
            qs = qs.filter(resource_type=resource_type)
        if user_id:
            qs = qs.filter(user_id=user_id)
        return qs

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """审计统计：各操作类型计数。"""
        from django.db.models import Count
        data = list(
            AuditLog.objects.values('action').annotate(count=Count('id')).order_by('-count')
        )
        return ok(data)
