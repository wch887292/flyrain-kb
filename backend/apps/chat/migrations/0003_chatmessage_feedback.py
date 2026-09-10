from django.db import migrations, models


class Migration(migrations.Migration):
    """为 ChatMessage 添加用户反馈字段（点赞/点踩 + 备注）。"""

    dependencies = [
        ('chat', '0002_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='chatmessage',
            name='feedback',
            field=models.CharField(
                blank=True, choices=[('like', '点赞'), ('dislike', '点踩')],
                max_length=10, null=True, verbose_name='用户反馈',
            ),
        ),
        migrations.AddField(
            model_name='chatmessage',
            name='feedback_comment',
            field=models.TextField(blank=True, default='', verbose_name='反馈备注'),
        ),
    ]
