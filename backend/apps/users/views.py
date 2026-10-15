from rest_framework import status, viewsets
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.common.rbac import RoleRequiredMixin, ROLE_ADMIN
from apps.common.utils import get_request_tenant, ok, fail
from apps.users.serializers import (
    LoginSerializer, RegisterSerializer, UserSerializer, AdminUserWriteSerializer
)
from apps.users.models import User, ApiKey


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


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    """用户修改自己的密码。修改成功后清除 must_change_password 标志。"""
    old_password = request.data.get('old_password', '')
    new_password = request.data.get('new_password', '')
    if not old_password or not new_password:
        return fail('旧密码和新密码不能为空', code=400)
    if len(new_password) < 6:
        return fail('新密码长度不能少于6位', code=400)
    user = request.user
    if not user.check_password(old_password):
        return fail('旧密码错误', code=400)
    user.set_password(new_password)
    user.must_change_password = False
    user.save(update_fields=['password', 'must_change_password'])
    return ok(message='密码修改成功')


class UserViewSet(RoleRequiredMixin, viewsets.ModelViewSet):
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
        if instance.id == self.request.user.id:
            raise ValidationError('不能删除当前登录的账号')
        if instance.role == ROLE_ADMIN and User.objects.filter(role=ROLE_ADMIN).count() <= 1:
            raise ValidationError('至少需保留一名管理员')
        super().perform_destroy(instance)


class ApiKeyViewSet(viewsets.ModelViewSet):
    """API Key 管理：用户可创建、查看、删除自己的 API Key。"""
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return ApiKey.objects.filter(user=self.request.user).order_by('-create_time')

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        return ok([{
            'id': k.id, 'name': k.name, 'key_prefix': k.key_prefix,
            'status': k.status, 'call_count': k.call_count,
            'last_used_at': k.last_used_at.strftime('%Y-%m-%d %H:%M:%S') if k.last_used_at else None,
            'expires_at': k.expires_at.strftime('%Y-%m-%d %H:%M:%S') if k.expires_at else None,
            'create_time': k.create_time.strftime('%Y-%m-%d %H:%M:%S'),
        } for k in qs])

    def create(self, request, *args, **kwargs):
        name = request.data.get('name', '')
        if not name:
            return fail('名称必填', code=400)
        tenant = get_request_tenant(request)
        api_key = ApiKey.objects.create(
            name=name, user=request.user, tenant=tenant, status='active',
        )
        return ok({
            'id': api_key.id, 'name': api_key.name,
            'key': api_key.key,  # 仅创建时返回完整 key
            'key_prefix': api_key.key_prefix,
            'create_time': api_key.create_time.strftime('%Y-%m-%d %H:%M:%S'),
        }, message='API Key 已创建，请妥善保存（仅显示一次）')

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.user_id != request.user.id:
            return fail('无权限', code=403)
        instance.delete()
        return ok({}, message='已删除')

    @action(detail=True, methods=['post'])
    def toggle(self, request, pk=None):
        """启用/禁用 API Key。"""
        instance = self.get_object()
        if instance.user_id != request.user.id:
            return fail('无权限', code=403)
        instance.status = 'disabled' if instance.status == 'active' else 'active'
        instance.save(update_fields=['status'])
        return ok({'status': instance.status}, message=f'已{"禁用" if instance.status == "disabled" else "启用"}')
