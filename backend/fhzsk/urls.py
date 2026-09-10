from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

from apps.common.api_v1 import chat_api, search_api

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/users/', include("apps.users.urls")),
    path('api/knowledge/', include("apps.knowledge.urls")),
    path('api/application/', include("apps.application.urls")),
    path('api/chat/', include("apps.chat.urls")),
    path('api/model/', include("apps.model_provider.urls")),
    path('api/common/', include("apps.common.urls")),
    # 对外 API v1（API Key 认证）
    path('api/v1/chat/', chat_api, name='api-v1-chat'),
    path('api/v1/search/', search_api, name='api-v1-search'),
    # API 文档
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
