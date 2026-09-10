from django.db import migrations, models


class Migration(migrations.Migration):
    """ModelProvider 添加 supports_vision 字段。"""

    dependencies = [
        ('model_provider', '0004_model_pricing'),
    ]

    operations = [
        migrations.AddField(
            model_name='modelprovider',
            name='supports_vision',
            field=models.BooleanField(default=False, verbose_name='支持视觉理解'),
        ),
    ]
