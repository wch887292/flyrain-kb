from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    """知识库权限细化 + 多模态标记 + 分段块类型。"""

    dependencies = [
        ('knowledge', '0003_paragraph_search_vector_gin'),
        ('users', '0001_initial'),
    ]

    operations = [
        # 知识库授权用户
        migrations.AddField(
            model_name='knowledgebase',
            name='authorized_users',
            field=models.ManyToManyField(blank=True, related_name='authorized_kbs',
                                           to='users.user', verbose_name='授权用户'),
        ),
        # 文档多模态标记
        migrations.AddField(
            model_name='document',
            name='has_images',
            field=models.BooleanField(default=False, verbose_name='含图片'),
        ),
        migrations.AddField(
            model_name='document',
            name='has_tables',
            field=models.BooleanField(default=False, verbose_name='含表格'),
        ),
        migrations.AddField(
            model_name='document',
            name='image_count',
            field=models.IntegerField(default=0, verbose_name='图片数'),
        ),
        migrations.AddField(
            model_name='document',
            name='table_count',
            field=models.IntegerField(default=0, verbose_name='表格数'),
        ),
        # 分段块类型
        migrations.AddField(
            model_name='paragraph',
            name='block_type',
            field=models.CharField(
                choices=[('text', '文本'), ('table', '表格'), ('image', '图片')],
                default='text', max_length=10, verbose_name='块类型',
            ),
        ),
    ]
