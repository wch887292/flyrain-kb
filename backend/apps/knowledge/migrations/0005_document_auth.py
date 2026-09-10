from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    """文档级权限：Document 添加 authorized_users。"""

    dependencies = [
        ('knowledge', '0004_kb_auth_multimodal'),
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='authorized_users',
            field=models.ManyToManyField(blank=True, related_name='authorized_docs',
                                           to='users.user', verbose_name='文档授权用户'),
        ),
    ]
