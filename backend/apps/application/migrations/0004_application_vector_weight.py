from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):
    """为 AI 应用添加 vector_weight 字段，支持混合检索权重可配置。"""

    dependencies = [
        ('application', '0003_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='application',
            name='vector_weight',
            field=models.FloatField(
                default=0.7,
                validators=[
                    django.core.validators.MinValueValidator(0.0),
                    django.core.validators.MaxValueValidator(1.0),
                ],
                verbose_name='向量检索权重',
            ),
        ),
    ]
