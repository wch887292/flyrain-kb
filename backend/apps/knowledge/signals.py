"""信号：Paragraph 保存时自动更新全文检索向量 search_vector。"""
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.postgres.search import SearchVector

from apps.knowledge.models import Paragraph


@receiver(post_save, sender=Paragraph)
def update_search_vector(sender, instance, created, **kwargs):
    """保存后异步更新 search_vector（避免递归，用 update 不走 save）。"""
    if not instance.content:
        return
    config = getattr(settings, 'SEARCH_CONFIG', 'simple')
    # 用 QuerySet.update 不触发 post_save，避免递归
    Paragraph.objects.filter(pk=instance.pk).update(
        search_vector=SearchVector('content', config=config)
    )
