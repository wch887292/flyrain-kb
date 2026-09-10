from django.db import migrations, models
import django.db.models.deletion
import django.conf


class Migration(migrations.Migration):
    """多智能体协作 + MCP + 评价优化 + 文件上传 + 分享发布。"""

    dependencies = [
        ('application', '0009_agent_message_images'),
        migrations.swappable_dependency(django.conf.settings.AUTH_USER_MODEL),
    ]

    operations = [
        # 新建 MCPServer
        migrations.CreateModel(
            name='MCPServer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='名称')),
                ('transport', models.CharField(choices=[('stdio', '标准输入输出'), ('http', 'HTTP/SSE')], default='http', max_length=20, verbose_name='传输方式')),
                ('url', models.CharField(blank=True, default='', max_length=500, verbose_name='服务器地址')),
                ('command', models.CharField(blank=True, default='', max_length=500, verbose_name='启动命令(stdio)')),
                ('args', models.JSONField(default=list, verbose_name='启动参数')),
                ('env', models.JSONField(default=dict, verbose_name='环境变量')),
                ('headers', models.JSONField(default=dict, verbose_name='请求头')),
                ('tools_cache', models.JSONField(default=list, verbose_name='工具列表缓存')),
                ('is_active', models.BooleanField(default=True, verbose_name='是否启用')),
                ('create_time', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('update_time', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='mcp_servers', to='users.tenant', verbose_name='租户')),
            ],
            options={
                'verbose_name': 'MCP 服务器',
                'verbose_name_plural': 'MCP 服务器',
                'ordering': ['-create_time'],
            },
        ),
        # Agent 新增字段
        migrations.AddField(
            model_name='agent',
            name='enable_auto_optimize',
            field=models.BooleanField(default=False, verbose_name='启用自动优化'),
        ),
        migrations.AddField(
            model_name='agent',
            name='is_public',
            field=models.BooleanField(default=False, verbose_name='是否公开'),
        ),
        migrations.AddField(
            model_name='agent',
            name='share_code',
            field=models.CharField(blank=True, default='', max_length=32, verbose_name='分享码'),
        ),
        migrations.AddField(
            model_name='agent',
            name='share_config',
            field=models.JSONField(default=dict, verbose_name='分享配置'),
        ),
        migrations.AddField(
            model_name='agent',
            name='mcp_servers',
            field=models.ManyToManyField(blank=True, related_name='agents', to='application.mcpserver', verbose_name='MCP 服务器'),
        ),
        migrations.AddField(
            model_name='agent',
            name='sub_agents',
            field=models.ManyToManyField(blank=True, related_name='parent_agents', symmetrical=False, to='application.agent', verbose_name='子智能体'),
        ),
        # 新建 AgentFile
        migrations.CreateModel(
            name='AgentFile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file_name', models.CharField(max_length=255, verbose_name='文件名')),
                ('file_path', models.CharField(max_length=500, verbose_name='文件路径')),
                ('file_size', models.BigIntegerField(default=0, verbose_name='文件大小(字节)')),
                ('file_type', models.CharField(max_length=50, verbose_name='文件类型')),
                ('create_time', models.DateTimeField(auto_now_add=True, verbose_name='上传时间')),
                ('conversation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='files', to='application.agentconversation', verbose_name='会话')),
                ('uploader', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=django.conf.settings.AUTH_USER_MODEL, verbose_name='上传者')),
            ],
            options={
                'verbose_name': '智能体文件',
                'verbose_name_plural': '智能体文件',
                'ordering': ['-create_time'],
            },
        ),
        # 新建 AgentEvaluation
        migrations.CreateModel(
            name='AgentEvaluation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('score', models.IntegerField(choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')], default=3, verbose_name='综合评分')),
                ('relevance_score', models.IntegerField(default=3, verbose_name='相关性评分')),
                ('accuracy_score', models.IntegerField(default=3, verbose_name='准确性评分')),
                ('completeness_score', models.IntegerField(default=3, verbose_name='完整性评分')),
                ('feedback', models.TextField(blank=True, default='', verbose_name='评价内容')),
                ('suggestion', models.TextField(blank=True, default='', verbose_name='优化建议')),
                ('suggested_prompt', models.TextField(blank=True, default='', verbose_name='建议的系统提示词')),
                ('applied', models.BooleanField(default=False, verbose_name='是否已应用')),
                ('create_time', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('agent', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='evaluations', to='application.agent', verbose_name='智能体')),
                ('conversation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='evaluations', to='application.agentconversation', verbose_name='会话')),
            ],
            options={
                'verbose_name': '智能体评价',
                'verbose_name_plural': '智能体评价',
                'ordering': ['-create_time'],
            },
        ),
    ]
