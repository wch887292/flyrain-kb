from django.db import migrations, models


class Migration(migrations.Migration):
    """Agent 增加 enable_code_interpreter 字段。"""

    dependencies = [
        ('application', '0007_agent'),
    ]

    operations = [
        migrations.AddField(
            model_name='agent',
            name='enable_code_interpreter',
            field=models.BooleanField(default=False, verbose_name='启用代码执行'),
        ),
    ]
