from django.db import models
from django.conf import settings


class CommonBaseModel(models.Model):
    """公共基类：统一时间戳"""
    create_time = models.DateTimeField(auto_now_add=True)
    update_time = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class AuditLog(models.Model):
    """操作审计日志：记录用户的关键写操作"""
    ACTION_CHOICES = (
        ('login', '登录'),
        ('logout', '登出'),
        ('create', '创建'),
        ('update', '更新'),
        ('delete', '删除'),
        ('upload', '上传'),
        ('reparse', '重新解析'),
        ('chat', '对话'),
        ('other', '其他'),
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                             null=True, blank=True, related_name='audit_logs',
                             verbose_name="操作用户")
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, default='other',
                              verbose_name="操作类型")
    resource_type = models.CharField(max_length=50, blank=True, default='',
                                     verbose_name="资源类型")
    resource_id = models.IntegerField(null=True, blank=True, verbose_name="资源ID")
    detail = models.TextField(blank=True, default='', verbose_name="操作详情")
    ip = models.GenericIPAddressField(null=True, blank=True, verbose_name="IP地址")
    path = models.CharField(max_length=255, blank=True, default='', verbose_name="请求路径")
    method = models.CharField(max_length=10, blank=True, default='', verbose_name="请求方法")
    status_code = models.IntegerField(null=True, blank=True, verbose_name="响应状态码")
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="操作时间")

    class Meta:
        verbose_name = "审计日志"
        verbose_name_plural = "审计日志"
        ordering = ['-create_time']
        indexes = [
            models.Index(fields=['user', '-create_time']),
            models.Index(fields=['action', '-create_time']),
        ]

    def __str__(self):
        return f'{self.user} {self.action} {self.resource_type}#{self.resource_id}'
