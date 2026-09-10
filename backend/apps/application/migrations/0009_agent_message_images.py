from django.db import migrations, models


class Migration(migrations.Migration):
    """AgentMessage 增加 images 字段。"""

    dependencies = [
        ('application', '0008_agent_code_interpreter'),
    ]

    operations = [
        migrations.AddField(
            model_name='agentmessage',
            name='images',
            field=models.JSONField(default=list, verbose_name='生成的图片(base64)'),
        ),
    ]
