from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.application.views import ApplicationViewSet, WorkflowViewSet, PluginViewSet
from apps.application.agent_views import (
    AgentViewSet, agent_conversations, agent_history, agent_chat
)
from apps.application.agent_templates import list_templates, create_from_template
from apps.application.mcp_market import list_mcp_templates, add_mcp_from_template
from apps.application.agent_extra import (
    MCPServerViewSet, upload_file, list_files,
    evaluate, list_evaluations, apply_evaluation,
    share_agent, get_shared_agent,
    publish_version, list_versions, rollback_version, compare_versions,
    sandbox_status,
)

router = DefaultRouter()
router.register(r'apps', ApplicationViewSet, basename='application')
router.register(r'workflows', WorkflowViewSet, basename='workflow')
router.register(r'plugins', PluginViewSet, basename='plugin')
router.register(r'agents', AgentViewSet, basename='agent')
router.register(r'mcp-servers', MCPServerViewSet, basename='mcp-server')

urlpatterns = [
    path('', include(router.urls)),
    path('agent/conversations/', agent_conversations, name='agent-conversations'),
    path('agent/history/', agent_history, name='agent-history'),
    path('agent/chat/', agent_chat, name='agent-chat'),
    path('agent/templates/', list_templates, name='agent-templates'),
    path('agent/templates/create/', create_from_template, name='agent-template-create'),
    path('agent/upload/', upload_file, name='agent-upload'),
    path('agent/files/', list_files, name='agent-files'),
    path('agent/evaluate/', evaluate, name='agent-evaluate'),
    path('agent/evaluations/', list_evaluations, name='agent-evaluations'),
    path('agent/apply-evaluation/', apply_evaluation, name='agent-apply-evaluation'),
    path('agent/share/', share_agent, name='agent-share'),
    path('agent/shared/<str:share_code>/', get_shared_agent, name='agent-shared'),
    # 版本管理
    path('agent/versions/publish/', publish_version, name='agent-version-publish'),
    path('agent/versions/', list_versions, name='agent-versions'),
    path('agent/versions/rollback/', rollback_version, name='agent-version-rollback'),
    path('agent/versions/compare/', compare_versions, name='agent-version-compare'),
    # 沙箱状态
    path('agent/sandbox-status/', sandbox_status, name='agent-sandbox-status'),
    # MCP 市场
    path('mcp-market/templates/', list_mcp_templates, name='mcp-market-templates'),
    path('mcp-market/add/', add_mcp_from_template, name='mcp-market-add'),
]
