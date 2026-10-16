from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone
from datetime import timedelta
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.utils import get_request_tenant, ok, fail
from apps.common.rbac import RoleRequiredMixin, ROLE_ADMIN
from apps.model_provider.models import ModelProvider, ModelUsage
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
        self._check_write()
        tenant = get_request_tenant(self.request)
        serializer.save(tenant=tenant)

    @action(detail=False, methods=['post'])
    def test(self, request):
        s = ModelTestSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        data = s.validated_data
        try:
            from openai import OpenAI
            client = OpenAI(api_key=data['api_key'], base_url=data['base_url'])
            if data['type'] == 'embedding':
                resp = client.embeddings.create(
                    model=data['model_name'], input=["连通性测试"]
                )
                dim = len(resp.data[0].embedding)
                return Response({'success': True, 'dim': dim})
            else:
                resp = client.chat.completions.create(
                    model=data['model_name'],
                    messages=[{"role": "user", "content": "ping"}],
                    max_tokens=16,
                )
                reply = resp.choices[0].message.content or ""
                return Response({'success': bool(reply), 'reply': reply[:50]})
        except Exception as e:  # noqa
            return Response({'success': False, 'message': str(e)},
                            status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def test_connection(self, request, pk=None):
        """用已保存的模型配置测试连通性（无需暴露 api_key）。"""
        provider = self.get_object()
        try:
            from openai import OpenAI
            client = OpenAI(api_key=provider.api_key, base_url=provider.base_url)
            if provider.type == 'embedding':
                resp = client.embeddings.create(
                    model=provider.model_name, input=["连通性测试"]
                )
                dim = len(resp.data[0].embedding)
                return Response({'success': True, 'dim': dim})
            else:
                resp = client.chat.completions.create(
                    model=provider.model_name,
                    messages=[{"role": "user", "content": "ping"}],
                    max_tokens=16,
                )
                reply = resp.choices[0].message.content or ""
                return Response({'success': bool(reply), 'reply': reply[:50]})
        except Exception as e:  # noqa
            return Response({'success': False, 'message': str(e)},
                            status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def usage_stats(self, request):
        """模型调用成本分析统计（仅 admin）。
        query: days=7（统计最近 N 天）, model_type=llm|embedding（可选）
        返回：总调用数、Token 消耗、估算成本、按天趋势、按模型分布、按用户分布。
        """
        self._check_read()
        days = int(request.query_params.get('days', 7))
        model_type = request.query_params.get('model_type')
        since = timezone.now() - timedelta(days=days)

        qs = ModelUsage.objects.filter(create_time__gte=since, status='success')
        tenant = get_request_tenant(request)
        if tenant:
            qs = qs.filter(user__tenant=tenant)
        if model_type:
            qs = qs.filter(model_type=model_type)

        # 总体统计
        agg = qs.aggregate(
            total_calls=Count('id'),
            total_prompt_tokens=Sum('prompt_tokens'),
            total_completion_tokens=Sum('completion_tokens'),
            total_tokens=Sum('total_tokens'),
            avg_duration=Avg('duration_ms'),
        )

        # 按模型统计（同时用于成本计算，避免遍历所有记录）
        by_model_qs = (
            qs.values('model_name', 'model_type')
            .annotate(
                calls=Count('id'),
                total_tokens=Sum('total_tokens'),
                prompt_tokens=Sum('prompt_tokens'),
                completion_tokens=Sum('completion_tokens'),
            )
            .order_by('-total_tokens')
        )
        by_model_all = list(by_model_qs)

        # 估算成本：按模型单价计算（只需遍历按模型分组的结果）
        total_cost = 0.0
        by_model_cost = {}
        providers = ModelProvider.objects.all()
        if tenant:
            providers = providers.filter(tenant=tenant)
        provider_map = {p.model_name: p for p in providers}

        for m in by_model_all:
            p = provider_map.get(m['model_name'])
            if p and p.price_input_per_1m and p.price_output_per_1m:
                cost = (m['prompt_tokens'] / 1_000_000 * p.price_input_per_1m +
                        m['completion_tokens'] / 1_000_000 * p.price_output_per_1m)
                total_cost += cost
                by_model_cost[m['model_name']] = cost

        # 按天统计
        daily = list(
            qs.extra(select={'day': 'DATE(model_provider_modelusage.create_time)'})
            .values('day')
            .annotate(
                calls=Count('id'),
                prompt_tokens=Sum('prompt_tokens'),
                completion_tokens=Sum('completion_tokens'),
                total_tokens=Sum('total_tokens'),
            )
            .order_by('day')
        )

        # 按模型统计（取前10）
        by_model = by_model_all[:10]
        for m in by_model:
            m['estimated_cost'] = round(by_model_cost.get(m['model_name'], 0), 6)

        # 按用户统计
        by_user = list(
            qs.filter(user__isnull=False)
            .values('user__username', 'user__nickname')
            .annotate(
                calls=Count('id'),
                total_tokens=Sum('total_tokens'),
            )
            .order_by('-total_tokens')[:10]
        )

        return ok({
            'period_days': days,
            'total_calls': agg['total_calls'] or 0,
            'total_prompt_tokens': agg['total_prompt_tokens'] or 0,
            'total_completion_tokens': agg['total_completion_tokens'] or 0,
            'total_tokens': agg['total_tokens'] or 0,
            'avg_duration_ms': round(agg['avg_duration'] or 0, 1),
            'total_estimated_cost': round(total_cost, 6),
            'daily': daily,
            'by_model': by_model,
            'by_user': by_user,
        })
