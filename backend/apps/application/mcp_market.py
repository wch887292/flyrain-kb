"""MCP 工具市场：预设常用 MCP 服务器模板，一键添加。"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.utils import get_request_tenant, ok, fail
from apps.application.models import MCPServer


# 预设 MCP 服务器模板库
MCP_TEMPLATES = [
    {
        'id': 'filesystem',
        'name': '文件系统',
        'icon': '📁',
        'category': '系统',
        'description': '访问本地文件系统，读取、创建、编辑文件和目录',
        'transport': 'stdio',
        'command': 'npx',
        'args': ['-y', '@modelcontextprotocol/server-filesystem', '/data'],
        'env': {},
        'url': '',
        'headers': {},
    },
    {
        'id': 'github',
        'name': 'GitHub',
        'icon': '🐙',
        'category': '开发',
        'description': '管理 GitHub 仓库、Issues、PR、代码搜索',
        'transport': 'stdio',
        'command': 'npx',
        'args': ['-y', '@modelcontextprotocol/server-github'],
        'env': {'GITHUB_PERSONAL_ACCESS_TOKEN': 'your-token-here'},
        'url': '',
        'headers': {},
    },
    {
        'id': 'slack',
        'name': 'Slack',
        'icon': '💬',
        'category': '协作',
        'description': '发送消息、读取频道、管理 Slack 工作区',
        'transport': 'stdio',
        'command': 'npx',
        'args': ['-y', '@modelcontextprotocol/server-slack'],
        'env': {'SLACK_BOT_TOKEN': 'your-token-here'},
        'url': '',
        'headers': {},
    },
    {
        'id': 'notion',
        'name': 'Notion',
        'icon': '📝',
        'category': '笔记',
        'description': '读取和创建 Notion 页面、数据库、内容块',
        'transport': 'stdio',
        'command': 'npx',
        'args': ['-y', '@notionhq/notion-mcp-server'],
        'env': {'NOTION_TOKEN': 'your-token-here'},
        'url': '',
        'headers': {},
    },
    {
        'id': 'postgres',
        'name': 'PostgreSQL',
        'icon': '🐘',
        'category': '数据库',
        'description': '查询 PostgreSQL 数据库，执行 SQL、分析数据',
        'transport': 'stdio',
        'command': 'npx',
        'args': ['-y', '@modelcontextprotocol/server-postgres', 'postgresql://user:pass@localhost:5432/db'],
        'env': {},
        'url': '',
        'headers': {},
    },
    {
        'id': 'sqlite',
        'name': 'SQLite',
        'icon': '🗄️',
        'category': '数据库',
        'description': '查询 SQLite 数据库文件，执行 SQL 分析',
        'transport': 'stdio',
        'command': 'npx',
        'args': ['-y', '@modelcontextprotocol/server-sqlite', '/data/db.sqlite'],
        'env': {},
        'url': '',
        'headers': {},
    },
    {
        'id': 'fetch',
        'name': '网页抓取',
        'icon': '🌐',
        'category': '网络',
        'description': '抓取网页内容，提取正文、链接、元数据',
        'transport': 'stdio',
        'command': 'npx',
        'args': ['-y', '@modelcontextprotocol/server-fetch'],
        'env': {},
        'url': '',
        'headers': {},
    },
    {
        'id': 'memory',
        'name': '记忆存储',
        'icon': '🧠',
        'category': 'AI',
        'description': '持久化记忆存储，保存和检索对话记忆、知识',
        'transport': 'stdio',
        'command': 'npx',
        'args': ['-y', '@modelcontextprotocol/server-memory'],
        'env': {},
        'url': '',
        'headers': {},
    },
    {
        'id': 'google-drive',
        'name': 'Google Drive',
        'icon': '📂',
        'category': '云存储',
        'description': '访问 Google Drive 文件，搜索、读取、上传',
        'transport': 'stdio',
        'command': 'npx',
        'args': ['-y', '@modelcontextprotocol/server-google-drive'],
        'env': {'GOOGLE_CLIENT_ID': '', 'GOOGLE_CLIENT_SECRET': ''},
        'url': '',
        'headers': {},
    },
    {
        'id': 'linear',
        'name': 'Linear',
        'icon': '📋',
        'category': '项目管理',
        'description': '管理 Linear 项目、任务、Issue，查询和创建',
        'transport': 'stdio',
        'command': 'npx',
        'args': ['-y', '@linear/mcp'],
        'env': {'LINEAR_API_KEY': 'your-key-here'},
        'url': '',
        'headers': {},
    },
    {
        'id': 'seqlog',
        'name': 'Seq 日志',
        'icon': '📊',
        'category': '运维',
        'description': '查询 Seq 日志服务器，搜索和分析应用日志',
        'transport': 'http',
        'command': '',
        'args': [],
        'env': {},
        'url': 'http://localhost:5341',
        'headers': {'X-Seq-ApiKey': 'your-key-here'},
    },
    {
        'id': 'custom-http',
        'name': '自定义 HTTP',
        'icon': '🔌',
        'category': '自定义',
        'description': '连接任意符合 MCP 协议的 HTTP/SSE 服务器',
        'transport': 'http',
        'command': '',
        'args': [],
        'env': {},
        'url': 'https://your-mcp-server.example.com',
        'headers': {},
    },
]


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_mcp_templates(request):
    """获取 MCP 模板列表。query: category（可选筛选）"""
    category = request.query_params.get('category')
    templates = MCP_TEMPLATES
    if category:
        templates = [t for t in templates if t['category'] == category]

    categories = sorted(set(t['category'] for t in MCP_TEMPLATES))
    return ok({'categories': categories, 'templates': templates})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_mcp_from_template(request):
    """从模板添加 MCP 服务器。body: {template_id, name?, config_overrides?}"""
    template_id = request.data.get('template_id')
    custom_name = request.data.get('name')
    overrides = request.data.get('config_overrides', {}) or {}

    template = next((t for t in MCP_TEMPLATES if t['id'] == template_id), None)
    if not template:
        return fail('模板不存在', code=404)

    tenant = get_request_tenant(request)
    server = MCPServer.objects.create(
        tenant=tenant,
        name=custom_name or template['name'],
        transport=overrides.get('transport', template['transport']),
        url=overrides.get('url', template['url']),
        command=overrides.get('command', template['command']),
        args=overrides.get('args', template['args']),
        env=overrides.get('env', template['env']),
        headers=overrides.get('headers', template['headers']),
        is_active=True,
    )

    return ok({
        'id': server.id,
        'name': server.name,
        'message': f'已从模板「{template["name"]}」添加 MCP 服务器',
    })
