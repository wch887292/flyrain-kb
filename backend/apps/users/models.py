import secrets

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
    must_change_password = models.BooleanField(default=True, verbose_name="需修改密码")
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        verbose_name = "用户"
        verbose_name_plural = "用户"

    def __str__(self):
        return self.username


class ApiKey(models.Model):
    """API Key：对外提供 API 访问凭证"""
    STATUS = (
        ('active', '启用'),
        ('disabled', '禁用'),
    )
    name = models.CharField(max_length=100, verbose_name="名称")
    key = models.CharField(max_length=64, unique=True, verbose_name="API Key")
    key_prefix = models.CharField(max_length=16, verbose_name="Key 前缀（用于展示）")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='api_keys',
                             verbose_name="所属用户")
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='api_keys',
                               verbose_name="所属租户")
    status = models.CharField(max_length=20, choices=STATUS, default='active', verbose_name="状态")
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name="过期时间")
    last_used_at = models.DateTimeField(null=True, blank=True, verbose_name="最后使用时间")
    call_count = models.IntegerField(default=0, verbose_name="调用次数")
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        verbose_name = "API Key"
        verbose_name_plural = "API Key"
        ordering = ['-create_time']

    def __str__(self):
        return f'{self.name}({self.key_prefix}...)'

    @classmethod
    def generate_key(cls):
        """生成 API Key：fk- + 48位随机十六进制"""
        return 'fk-' + secrets.token_hex(24)

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.generate_key()
            self.key_prefix = self.key[:16]
        super().save(*args, **kwargs)
