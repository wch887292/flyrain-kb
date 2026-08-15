from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/users/', include("apps.users.urls")),
    path('api/knowledge/', include("apps.knowledge.urls")),
    path('api/application/', include("apps.application.urls")),
    path('api/chat/', include("apps.chat.urls")),
    path('api/model/', include("apps.model_provider.urls")),
]
