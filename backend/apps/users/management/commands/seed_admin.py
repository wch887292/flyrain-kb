"""创建首个管理员账户（RBAC 种子数据）。

用法：
    python manage.py seed_admin --username admin --password admin123
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.users.models import Tenant

User = get_user_model()


class Command(BaseCommand):
    help = '创建首个管理员用户（role=admin）'

    def add_arguments(self, parser):
        parser.add_argument('--username', default='admin')
        parser.add_argument('--password', default='admin123')
        parser.add_argument('--email', default='admin@FHZSK.local')
        parser.add_argument('--tenant', default='默认租户')

    def handle(self, *args, **options):
        username = options['username']
        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(f'用户 {username} 已存在，跳过'))
            return
        tenant, _ = Tenant.objects.get_or_create(name=options['tenant'])
        user = User.objects.create_user(
            username=username,
            email=options['email'],
            password=options['password'],
            tenant=tenant,
            role=ROLE_ADMIN,
        )
        from apps.common.rbac import ROLE_ADMIN  # noqa: imported for clarity
        user.is_staff = True
        user.is_superuser = True
        user.save(update_fields=['is_staff', 'is_superuser'])
        self.stdout.write(
            self.style.SUCCESS(f'管理员 {username}（{ROLE_ADMIN}）创建成功')
        )
