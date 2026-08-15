from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.model_provider.views import ModelProviderViewSet

router = DefaultRouter()
router.register(r'providers', ModelProviderViewSet, basename='provider')

urlpatterns = [
    path('', include(router.urls)),
]
