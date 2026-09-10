import secrets

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    """API Key 管理：ApiKey 模型。"""

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ApiKey',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='名称')),
                ('key', models.CharField(max_length=64, unique=True, verbose_name='API Key')),
                ('key_prefix', models.CharField(max_length=16, verbose_name='Key 前缀（用于展示）')),
                ('status', models.CharField(choices=[('active', '启用'), ('disabled', '禁用')], default='active', max_length=20, verbose_name='状态')),
                ('expires_at', models.DateTimeField(blank=True, null=True, verbose_name='过期时间')),
                ('last_used_at', models.DateTimeField(blank=True, null=True, verbose_name='最后使用时间')),
                ('call_count', models.IntegerField(default=0, verbose_name='调用次数')),
                ('create_time', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='api_keys', to='users.tenant', verbose_name='所属租户')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='api_keys', to='users.user', verbose_name='所属用户')),
            ],
            options={
                'verbose_name': 'API Key',
                'verbose_name_plural': 'API Key',
                'ordering': ['-create_time'],
            },
        ),
    ]
