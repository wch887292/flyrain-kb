from django.db import models
from django.conf import settings

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
    price_input_per_1m = models.FloatField(default=0, verbose_name="输入单价($/1M tokens)")
    price_output_per_1m = models.FloatField(default=0, verbose_name="输出单价($/1M tokens)")
    supports_vision = models.BooleanField(default=False, verbose_name="支持视觉理解")
    is_default = models.BooleanField(default=False, verbose_name="是否默认")
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True,
                               related_name='providers', verbose_name="租户")
    create_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "模型供应商"
        verbose_name_plural = "模型供应商"

    def __str__(self):
        return f'{self.name}({self.type})'


class ModelUsage(models.Model):
    """模型调用记录：Token 消耗、耗时、状态统计"""
    STATUS = (
        ('success', '成功'),
        ('failed', '失败'),
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                             null=True, blank=True, related_name='model_usages',
                             verbose_name="调用用户")
    app = models.ForeignKey('application.Application', on_delete=models.SET_NULL,
                            null=True, blank=True, related_name='model_usages',
                            verbose_name="关联应用")
    model_type = models.CharField(max_length=20, choices=ModelProvider.PROVIDER_TYPE,
                                  verbose_name="模型类型")
    model_name = models.CharField(max_length=200, verbose_name="模型名称")
    prompt_tokens = models.IntegerField(default=0, verbose_name="提示Token数")
    completion_tokens = models.IntegerField(default=0, verbose_name="补全Token数")
    total_tokens = models.IntegerField(default=0, verbose_name="总Token数")
    duration_ms = models.FloatField(default=0, verbose_name="耗时(毫秒)")
    status = models.CharField(max_length=10, choices=STATUS, default='success',
                              verbose_name="状态")
    error_msg = models.TextField(blank=True, default="", verbose_name="错误信息")
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="调用时间")

    class Meta:
        verbose_name = "模型调用记录"
        verbose_name_plural = "模型调用记录"
        ordering = ['-create_time']
        indexes = [
            models.Index(fields=['user', '-create_time']),
            models.Index(fields=['model_type', '-create_time']),
        ]

    def __str__(self):
        return f'{self.model_name}({self.total_tokens} tokens, {self.status})'
