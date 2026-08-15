from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.knowledge.views import (
    KnowledgeBaseViewSet, DocumentViewSet, search_view
)

router = DefaultRouter()
router.register(r'bases', KnowledgeBaseViewSet, basename='kb')
router.register(r'documents', DocumentViewSet, basename='document')

urlpatterns = [
    path('', include(router.urls)),
    path('search/', search_view, name='kb-search'),
]
