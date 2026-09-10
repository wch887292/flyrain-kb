from django.db import migrations, models
import django.db.models.deletion
import django.conf


class Migration(migrations.Migration):
    """智能体（Agent）：Agent / AgentConversation / AgentMessage。"""

    dependencies = [
        ('application', '0006_plugin'),
        ('knowledge', '0006_document_version'),
        migrations.swappable_dependency(django.conf.settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Agent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='名称')),
                ('avatar', models.CharField(blank=True, default='', max_length=500, verbose_name='头像URL')),
                ('description', models.TextField(blank=True, default='', verbose_name='描述')),
                ('role', models.CharField(blank=True, default='', max_length=200, verbose_name='角色设定')),
                ('system_prompt', models.TextField(blank=True, default='你是一个智能助手，可以使用提供的工具来回答用户问题。如果需要调用工具，请按照指定格式输出。', verbose_name='系统提示词')),
                ('temperature', models.FloatField(default=0.7, verbose_name='温度')),
                ('max_tokens', models.IntegerField(default=2048, verbose_name='最大Token')),
                ('max_iterations', models.IntegerField(default=5, verbose_name='最大推理轮次')),
                ('opening_message', models.TextField(blank=True, default='你好！我是你的智能助手，有什么可以帮你的？', verbose_name='开场白')),
                ('suggested_questions', models.JSONField(default=list, verbose_name='建议问题')),
                ('enable_reasoning', models.BooleanField(default=True, verbose_name='展示思考过程')),
                ('is_active', models.BooleanField(default=True, verbose_name='是否启用')),
                ('create_time', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('update_time', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('kbs', models.ManyToManyField(blank=True, related_name='agents', to='knowledge.knowledgebase', verbose_name='关联知识库')),
                ('tools', models.ManyToManyField(blank=True, related_name='agents', to='application.plugin', verbose_name='可用工具')),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='agents', to='users.tenant', verbose_name='租户')),
            ],
            options={
                'verbose_name': '智能体',
                'verbose_name_plural': '智能体',
                'ordering': ['-create_time'],
            },
        ),
        migrations.CreateModel(
            name='AgentConversation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('session_id', models.CharField(max_length=64, unique=True, verbose_name='会话ID')),
                ('title', models.CharField(blank=True, default='新对话', max_length=200, verbose_name='标题')),
                ('create_time', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('update_time', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('agent', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='conversations', to='application.agent', verbose_name='智能体')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='agent_conversations', to=django.conf.settings.AUTH_USER_MODEL, verbose_name='用户')),
            ],
            options={
                'verbose_name': '智能体会话',
                'verbose_name_plural': '智能体会话',
                'ordering': ['-update_time'],
            },
        ),
        migrations.CreateModel(
            name='AgentMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[('user', '用户'), ('assistant', '助手'), ('tool', '工具')], max_length=20, verbose_name='角色')),
                ('content', models.TextField(verbose_name='内容')),
                ('reasoning', models.TextField(blank=True, default='', verbose_name='思考过程')),
                ('tool_calls', models.JSONField(default=list, verbose_name='工具调用记录')),
                ('tool_name', models.CharField(blank=True, default='', max_length=100, verbose_name='工具名称')),
                ('create_time', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('conversation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='application.agentconversation', verbose_name='会话')),
            ],
            options={
                'verbose_name': '智能体消息',
                'verbose_name_plural': '智能体消息',
                'ordering': ['create_time'],
            },
        ),
    ]
