from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    tenant_name = serializers.CharField(write_only=True, required=False, default="默认租户")

    class Meta:
        model = User
        fields = ('id', 'username', 'password', 'email', 'nickname',
                  'tenant_name')

    def create(self, validated_data):
        from apps.users.models import Tenant
        # RBAC：自注册只允许普通用户角色，管理员由 seed_admin 创建
        validated_data.pop('role', None)
        tenant_name = validated_data.pop('tenant_name', '默认租户')
        tenant, _ = Tenant.objects.get_or_create(name=tenant_name)
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.tenant = tenant
        user.role = 'user'
        user.save()
        return user


class LoginSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user
        data['username'] = user.username
        data['nickname'] = user.nickname
        data['role'] = user.role
        data['tenant'] = user.tenant.name if user.tenant else None
        return data


class UserSerializer(serializers.ModelSerializer):
    tenant = serializers.CharField(source='tenant.name', read_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'nickname', 'role', 'tenant', 'create_time')
        read_only_fields = ('id', 'create_time')


class AdminUserWriteSerializer(serializers.ModelSerializer):
    """管理员创建/编辑用户：可设置密码、角色、租户（仅写，不回显密码）。"""
    password = serializers.CharField(write_only=True, min_length=6, required=False)
    tenant_name = serializers.CharField(write_only=True, required=False, default='默认租户')

    class Meta:
        model = User
        fields = ('id', 'username', 'password', 'email', 'nickname', 'role', 'tenant_name')

    def create(self, validated_data):
        from apps.users.models import Tenant
        tenant_name = validated_data.pop('tenant_name', '默认租户')
        tenant, _ = Tenant.objects.get_or_create(name=tenant_name)
        password = validated_data.pop('password', None)
        user = User(
            username=validated_data.get('username'),
            email=validated_data.get('email', ''),
            nickname=validated_data.get('nickname', ''),
            role=validated_data.get('role', 'user'),
            tenant=tenant,
        )
        user.set_password(password or 'changeme123')
        user.save()
        return user

    def update(self, instance, validated_data):
        from apps.users.models import Tenant
        password = validated_data.pop('password', None)
        tenant_name = validated_data.pop('tenant_name', None)
        if tenant_name:
            tenant, _ = Tenant.objects.get_or_create(name=tenant_name)
            instance.tenant = tenant
        for attr in ('username', 'email', 'nickname', 'role'):
            if attr in validated_data:
                setattr(instance, attr, validated_data[attr])
        if password:
            instance.set_password(password)
        instance.save()
        return instance
