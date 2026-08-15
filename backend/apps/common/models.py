from django.db import models


class CommonBaseModel(models.Model):
    """公共基类：统一时间戳"""
    create_time = models.DateTimeField(auto_now_add=True)
    update_time = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
