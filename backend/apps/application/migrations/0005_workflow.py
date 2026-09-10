from django.db import migrations, models
import django.db.models.deletion
import django.conf


class Migration(migrations.Migration):
    """工作流编排：Workflow / WorkflowStep / WorkflowExecution。"""

    dependencies = [
        ('application', '0004_application_vector_weight'),
        ('users', '0001_initial'),
        migrations.swappable_dependency(django.conf.settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Workflow',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='名称')),
                ('desc', models.TextField(blank=True, default='', verbose_name='描述')),
                ('status', models.CharField(choices=[('draft', '草稿'), ('active', '启用'), ('archived', '归档')], default='draft', max_length=20, verbose_name='状态')),
                ('create_time', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('update_time', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='workflows', to='users.tenant', verbose_name='租户')),
            ],
            options={
                'verbose_name': '工作流',
                'verbose_name_plural': '工作流',
                'ordering': ['-create_time'],
            },
        ),
        migrations.CreateModel(
            name='WorkflowStep',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order', models.IntegerField(default=1, verbose_name='执行顺序')),
                ('name', models.CharField(max_length=100, verbose_name='步骤名称')),
                ('prompt', models.TextField(verbose_name='提示词模板')),
                ('temperature', models.FloatField(default=0.7, verbose_name='温度')),
                ('max_tokens', models.IntegerField(default=1024, verbose_name='最大Token')),
                ('create_time', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('workflow', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='steps', to='application.workflow', verbose_name='所属工作流')),
            ],
            options={
                'verbose_name': '工作流步骤',
                'verbose_name_plural': '工作流步骤',
                'ordering': ['order'],
            },
        ),
        migrations.CreateModel(
            name='WorkflowExecution',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('input_text', models.TextField(verbose_name='输入内容')),
                ('output_text', models.TextField(blank=True, default='', verbose_name='最终输出')),
                ('step_outputs', models.JSONField(default=list, verbose_name='各步骤输出')),
                ('status', models.CharField(choices=[('running', '执行中'), ('success', '成功'), ('failed', '失败')], default='running', max_length=20, verbose_name='状态')),
                ('error_msg', models.TextField(blank=True, default='', verbose_name='错误信息')),
                ('duration_ms', models.FloatField(default=0, verbose_name='耗时(毫秒)')),
                ('create_time', models.DateTimeField(auto_now_add=True, verbose_name='执行时间')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=django.conf.settings.AUTH_USER_MODEL, verbose_name='触发用户')),
                ('workflow', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='executions', to='application.workflow', verbose_name='工作流')),
            ],
            options={
                'verbose_name': '工作流执行记录',
                'verbose_name_plural': '工作流执行记录',
                'ordering': ['-create_time'],
            },
        ),
    ]
