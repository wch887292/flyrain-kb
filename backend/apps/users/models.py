from django.contrib.auth.models import AbstractUser
from django.db import models


class Tenant(models.Model):
    """租户：数据隔离的最小单位"""
    name = models.CharField(max_length=200, verbose_name="租户名称")
    desc = models.TextField(blank=True, default="", verbose_name="描述")
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        verbose_name = "租户"
        verbose_name_plural = "租户"

    def __str__(self):
        return self.name


class User(AbstractUser):
    """平台用户，归属某一租户"""
    ROLE_CHOICES = (
        ('admin', '管理员'),
        ('editor', '知识库维护'),
        ('user', '普通用户'),
    )
    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, null=True, blank=True,
        related_name='users', verbose_name="所属租户"
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user', verbose_name="角色")
    nickname = models.CharField(max_length=100, blank=True, default="", verbose_name="昵称")
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        verbose_name = "用户"
        verbose_name_plural = "用户"

    def __str__(self):
        return self.username
