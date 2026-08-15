from rest_framework import viewsets

from apps.application.models import Application
from apps.application.serializers import ApplicationSerializer
from apps.common.utils import get_request_tenant
from apps.common.rbac import RoleRequiredMixin, ROLE_ADMIN, ROLE_EDITOR


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
