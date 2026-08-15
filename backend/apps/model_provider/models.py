from django.db import models

from apps.users.models import Tenant


class ModelProvider(models.Model):
    """大模型 / Embedding 供应商配置（兼容 OpenAI 协议）"""
    PROVIDER_TYPE = (
        ('llm', '对话大模型'),
        ('embedding', '向量化模型'),
    )
    name = models.CharField(max_length=100, verbose_name="名称")
    type = models.CharField(max_length=20, choices=PROVIDER_TYPE, verbose_name="类型")
    base_url = models.CharField(max_length=500, verbose_name="API Base URL")
    api_key = models.CharField(max_length=500, verbose_name="API Key")
    model_name = models.CharField(max_length=200, verbose_name="模型名称")
    dimensions = models.IntegerField(default=1024, verbose_name="向量维度(embedding)")
    is_default = models.BooleanField(default=False, verbose_name="是否默认")
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True,
                               related_name='providers', verbose_name="租户")
    create_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "模型供应商"
        verbose_name_plural = "模型供应商"

    def __str__(self):
        return f'{self.name}({self.type})'
