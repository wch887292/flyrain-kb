from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.utils import get_request_tenant
from apps.common.rbac import RoleRequiredMixin, ROLE_ADMIN
from apps.model_provider.models import ModelProvider
from apps.model_provider.serializers import (
    ModelProviderSerializer, ModelTestSerializer
)
from apps.model_provider.llm_adapter import chat_completion, embed_texts


class ModelProviderViewSet(RoleRequiredMixin, viewsets.ModelViewSet):
    write_roles = (ROLE_ADMIN,)
    serializer_class = ModelProviderSerializer

    def get_queryset(self):
        tenant = get_request_tenant(self.request)
        qs = ModelProvider.objects.all()
        if tenant:
            qs = qs.filter(tenant=tenant)
        return qs.order_by('-create_time')

    def perform_create(self, serializer):
        self._check_role()
        tenant = get_request_tenant(self.request)
        serializer.save(tenant=tenant)

    @action(detail=False, methods=['post'])
    def test(self, request):
        s = ModelTestSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        data = s.validated_data
        try:
            if data['type'] == 'embedding':
                vec = embed_texts(["连通性测试"])
                ok = bool(vec and len(vec[0]) > 0)
                return Response({'success': ok, 'dim': len(vec[0]) if vec else 0})
            else:
                text = chat_completion(
                    [{"role": "user", "content": "ping"}], max_tokens=16
                )
                return Response({'success': bool(text), 'reply': text[:50]})
        except Exception as e:  # noqa
            return Response({'success': False, 'message': str(e)},
                            status=status.HTTP_400_BAD_REQUEST)
