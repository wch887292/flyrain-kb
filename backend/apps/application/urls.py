from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.application.views import ApplicationViewSet

router = DefaultRouter()
router.register(r'apps', ApplicationViewSet, basename='application')

urlpatterns = [
    path('', include(router.urls)),
]
