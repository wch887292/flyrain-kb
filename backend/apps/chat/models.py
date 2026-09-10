import uuid

from django.db import models

from apps.users.models import User
from apps.application.models import Application


class ChatMessage(models.Model):
    """对话消息记录"""
    ROLE = (
        ('user', '用户'),
        ('assistant', '助手'),
        ('system', '系统'),
    )
    FEEDBACK = (
        ('like', '点赞'),
        ('dislike', '点踩'),
    )
    session_id = models.CharField(max_length=64, default=uuid.uuid4, db_index=True,
                                  verbose_name="会话ID")
    app = models.ForeignKey(Application, on_delete=models.SET_NULL, null=True,
                            related_name='messages', verbose_name="应用")
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                             verbose_name="用户")
    role = models.CharField(max_length=20, choices=ROLE, verbose_name="角色")
    content = models.TextField(verbose_name="内容")
    # 用户反馈：点赞/点踩，仅 assistant 消息有意义
    feedback = models.CharField(max_length=10, choices=FEEDBACK, null=True, blank=True,
                                verbose_name="用户反馈")
    feedback_comment = models.TextField(blank=True, default="", verbose_name="反馈备注")
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        verbose_name = "对话消息"
        verbose_name_plural = "对话消息"
        ordering = ['create_time']
