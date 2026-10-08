from django.db import migrations, models


class Migration(migrations.Migration):
    """Agent 增加 enable_fhcode 字段（启用飞虹 Code 底层编程引擎）。"""

    dependencies = [
        ('application', '0011_agent_version'),
    ]

    operations = [
        migrations.AddField(
            model_name='agent',
            name='enable_fhcode',
            field=models.BooleanField(default=False, verbose_name='启用飞虹Code编程引擎'),
        ),
    ]
