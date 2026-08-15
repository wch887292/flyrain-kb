from rest_framework import status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.common.rbac import RoleRequiredMixin, ROLE_ADMIN
from apps.users.serializers import (
    LoginSerializer, RegisterSerializer, UserSerializer, AdminUserWriteSerializer
)
from apps.users.models import User


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    serializer = RegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()
    return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile(request):
    return Response(UserSerializer(request.user).data)


class UserViewSet(RoleRequiredMixin, viewsets.ModelViewSet):
    """用户管理（仅 admin 可读写）。返回扁平数组，便于前端管理表格直接渲染。"""
    queryset = User.objects.all().order_by('-create_time')
    serializer_class = UserSerializer
    read_roles = (ROLE_ADMIN,)
    write_roles = (ROLE_ADMIN,)
    pagination_class = None

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return AdminUserWriteSerializer
        return UserSerializer

    def perform_update(self, serializer):
        self._check_write()
        instance = serializer.instance
        new_role = serializer.validated_data.get('role')
        if (instance.role == ROLE_ADMIN and new_role and new_role != ROLE_ADMIN
                and User.objects.filter(role=ROLE_ADMIN).count() <= 1):
            raise ValidationError('至少需保留一名管理员，无法降级唯一管理员')
        super().perform_update(serializer)

    def perform_destroy(self, instance):
        self._check_write()
        # 防止删除自己
        if instance.id == self.request.user.id:
            raise ValidationError('不能删除当前登录的账号')
        # 防止删除最后一名管理员
        if instance.role == ROLE_ADMIN and User.objects.filter(role=ROLE_ADMIN).count() <= 1:
            raise ValidationError('至少需保留一名管理员')
        super().perform_destroy(instance)
