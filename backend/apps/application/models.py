from django.db import models

from apps.users.models import Tenant
from apps.knowledge.models import KnowledgeBase


class Application(models.Model):
    """AI 助手应用：绑定知识库 + Prompt 配置"""
    name = models.CharField(max_length=200, verbose_name="名称")
    desc = models.TextField(blank=True, default="", verbose_name="描述")
    kbs = models.ManyToManyField(KnowledgeBase, blank=True, related_name='apps',
                                 verbose_name="关联知识库")
    system_prompt = models.TextField(
        blank=True, default="你是一个基于企业知识库作答的助手，请只依据给定资料回答。",
        verbose_name="系统提示词")
    temperature = models.FloatField(default=0.7, verbose_name="温度")
    max_tokens = models.IntegerField(default=1024, verbose_name="最大Token")
    is_active = models.BooleanField(default=True, verbose_name="是否启用")
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='apps',
                               verbose_name="租户")
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        verbose_name = "AI 应用"
        verbose_name_plural = "AI 应用"

    def __str__(self):
        return self.name
