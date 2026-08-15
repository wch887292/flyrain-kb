from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from apps.users.views import LoginView, register, profile, UserViewSet

# UserViewSet 挂载到空前缀，配合主路由的 api/users/，
# 最终路径：GET/POST  /api/users/        （列表 / 新建）
#           GET/PUT/DELETE /api/users/<pk>/  （详情 / 改角色 / 删除）
router = DefaultRouter()
router.register(r'', UserViewSet, basename='user')

urlpatterns = [
    path('register/', register, name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('profile/', profile, name='profile'),
] + router.urls
