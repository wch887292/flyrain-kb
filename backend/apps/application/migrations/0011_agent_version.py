from django.db import migrations, models
import django.db.models.deletion
import django.conf


class Migration(migrations.Migration):
    """智能体版本发布与回滚。"""

    dependencies = [
        ('application', '0010_multi_agent_mcp_eval_file_share'),
        migrations.swappable_dependency(django.conf.settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AgentVersion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('version', models.CharField(max_length=20, verbose_name='版本号')),
                ('name', models.CharField(blank=True, default='', max_length=200, verbose_name='版本名称')),
                ('description', models.TextField(blank=True, default='', verbose_name='版本说明')),
                ('config_snapshot', models.JSONField(default=dict, verbose_name='配置快照')),
                ('is_current', models.BooleanField(default=False, verbose_name='是否当前版本')),
                ('is_published', models.BooleanField(default=False, verbose_name='是否已发布')),
                ('create_time', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('agent', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='versions', to='application.agent', verbose_name='智能体')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=django.conf.settings.AUTH_USER_MODEL, verbose_name='创建者')),
            ],
            options={
                'verbose_name': '智能体版本',
                'verbose_name_plural': '智能体版本',
                'ordering': ['-create_time'],
                'unique_together': {('agent', 'version')},
            },
        ),
    ]
