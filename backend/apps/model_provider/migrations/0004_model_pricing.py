from django.db import migrations, models


class Migration(migrations.Migration):
    """ModelProvider 添加成本核算价格字段。"""

    dependencies = [
        ('model_provider', '0003_model_usage'),
    ]

    operations = [
        migrations.AddField(
            model_name='modelprovider',
            name='price_input_per_1m',
            field=models.FloatField(default=0, verbose_name='输入单价($/1M tokens)'),
        ),
        migrations.AddField(
            model_name='modelprovider',
            name='price_output_per_1m',
            field=models.FloatField(default=0, verbose_name='输出单价($/1M tokens)'),
        ),
    ]
