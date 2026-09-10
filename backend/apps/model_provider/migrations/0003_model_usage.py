from django.db import migrations, models
import django.db.models.deletion
import django.conf


class Migration(migrations.Migration):
    """模型调用记录 ModelUsage：Token 消耗与耗时统计。"""

    dependencies = [
        ('model_provider', '0002_initial'),
        ('application', '0004_application_vector_weight'),
        migrations.swappable_dependency(django.conf.settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ModelUsage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('model_type', models.CharField(choices=[('llm', '对话大模型'), ('embedding', '向量化模型')], max_length=20, verbose_name='模型类型')),
                ('model_name', models.CharField(max_length=200, verbose_name='模型名称')),
                ('prompt_tokens', models.IntegerField(default=0, verbose_name='提示Token数')),
                ('completion_tokens', models.IntegerField(default=0, verbose_name='补全Token数')),
                ('total_tokens', models.IntegerField(default=0, verbose_name='总Token数')),
                ('duration_ms', models.FloatField(default=0, verbose_name='耗时(毫秒)')),
                ('status', models.CharField(choices=[('success', '成功'), ('failed', '失败')], default='success', max_length=10, verbose_name='状态')),
                ('error_msg', models.TextField(blank=True, default='', verbose_name='错误信息')),
                ('create_time', models.DateTimeField(auto_now_add=True, verbose_name='调用时间')),
                ('app', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='model_usages', to='application.application', verbose_name='关联应用')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='model_usages', to=django.conf.settings.AUTH_USER_MODEL, verbose_name='调用用户')),
            ],
            options={
                'verbose_name': '模型调用记录',
                'verbose_name_plural': '模型调用记录',
                'ordering': ['-create_time'],
            },
        ),
        migrations.AddIndex(
            model_name='modelusage',
            index=models.Index(fields=['user', '-create_time'], name='model_usage_user_id_idx'),
        ),
        migrations.AddIndex(
            model_name='modelusage',
            index=models.Index(fields=['model_type', '-create_time'], name='model_usage_type_idx'),
        ),
    ]
