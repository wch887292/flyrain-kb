from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from apps.users.views import LoginView, register, profile, UserViewSet, ApiKeyViewSet

router = DefaultRouter()
router.register(r'', UserViewSet, basename='user')
router.register(r'api-keys', ApiKeyViewSet, basename='api-key')

urlpatterns = [
    path('register/', register, name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('profile/', profile, name='profile'),
] + router.urls
