from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    """插件系统：Plugin 模型 + WorkflowStep.step_type + WorkflowStep.plugin。"""

    dependencies = [
        ('application', '0005_workflow'),
    ]

    operations = [
        migrations.CreateModel(
            name='Plugin',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='名称')),
                ('type', models.CharField(choices=[('http', 'HTTP 请求')], default='http', max_length=20, verbose_name='类型')),
                ('description', models.TextField(blank=True, default='', verbose_name='描述')),
                ('config', models.JSONField(default=dict, verbose_name='插件配置')),
                ('is_active', models.BooleanField(default=True, verbose_name='是否启用')),
                ('create_time', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='plugins', to='users.tenant', verbose_name='租户')),
            ],
            options={
                'verbose_name': '插件',
                'verbose_name_plural': '插件',
                'ordering': ['-create_time'],
            },
        ),
        migrations.AddField(
            model_name='workflowstep',
            name='step_type',
            field=models.CharField(choices=[('llm', 'LLM 调用'), ('plugin', '插件调用')], default='llm', max_length=20, verbose_name='步骤类型'),
        ),
        migrations.AddField(
            model_name='workflowstep',
            name='plugin',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='steps', to='application.plugin', verbose_name='调用插件'),
        ),
    ]
