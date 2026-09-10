"""RBAC 权限与用户管理安全护栏测试"""
from django.test import TestCase
from rest_framework.test import APIClient

from apps.users.models import User, Tenant
from apps.common.rbac import ROLE_ADMIN, ROLE_EDITOR, ROLE_USER


class TestRBAC(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="测试租户")
        self.admin = User.objects.create_user(
            username="admin", password="pass1234", role=ROLE_ADMIN, tenant=self.tenant
        )
        self.editor = User.objects.create_user(
            username="editor", password="pass1234", role=ROLE_EDITOR, tenant=self.tenant
        )
        self.user = User.objects.create_user(
            username="user", password="pass1234", role=ROLE_USER, tenant=self.tenant
        )
        self.client = APIClient()

    def _auth(self, user):
        self.client.force_authenticate(user=user)

    # ---- 注册接口 ----
    def test_register_creates_user_role_only(self):
        """自注册用户只能获得 user 角色，不能指定 admin/editor"""
        resp = self.client.post('/api/users/register/', {
            'username': 'newuser', 'password': 'pass1234', 'email': 'new@test.com'
        })
        self.assertEqual(resp.status_code, 201)
        u = User.objects.get(username='newuser')
        self.assertEqual(u.role, ROLE_USER)

    # ---- 用户管理接口（仅 admin） ----
    def test_admin_can_list_users(self):
        self._auth(self.admin)
        resp = self.client.get('/api/users/')
        self.assertEqual(resp.status_code, 200)

    def test_editor_cannot_list_users(self):
        self._auth(self.editor)
        resp = self.client.get('/api/users/')
        self.assertEqual(resp.status_code, 403)

    def test_user_cannot_list_users(self):
        self._auth(self.user)
        resp = self.client.get('/api/users/')
        self.assertEqual(resp.status_code, 403)

    def test_admin_can_create_user(self):
        self._auth(self.admin)
        resp = self.client.post('/api/users/', {
            'username': 'created', 'password': 'pass1234', 'role': ROLE_EDITOR
        })
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(User.objects.get(username='created').role, ROLE_EDITOR)

    def test_editor_cannot_create_user(self):
        self._auth(self.editor)
        resp = self.client.post('/api/users/', {
            'username': 'x', 'password': 'pass1234', 'role': ROLE_USER
        })
        self.assertEqual(resp.status_code, 403)

    # ---- 安全护栏 ----
    def test_cannot_delete_self(self):
        self._auth(self.admin)
        resp = self.client.delete(f'/api/users/{self.admin.id}/')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('不能删除', resp.data.get('detail', '') or resp.data.get('message', ''))

    def test_cannot_downgrade_last_admin(self):
        """唯一管理员不能被降级为非 admin"""
        self._auth(self.admin)
        resp = self.client.put(f'/api/users/{self.admin.id}/', {
            'username': 'admin', 'role': ROLE_EDITOR
        })
        self.assertEqual(resp.status_code, 400)

    def test_cannot_delete_last_admin(self):
        self._auth(self.admin)
        # 先创建另一个 admin，再删除它（确保至少有一个 admin 时可以删）
        other = User.objects.create_user(
            username="admin2", password="pass1234", role=ROLE_ADMIN, tenant=self.tenant
        )
        resp = self.client.delete(f'/api/users/{other.id}/')
        self.assertEqual(resp.status_code, 204)
        # 现在只剩一个 admin，不能删
        resp2 = self.client.delete(f'/api/users/{self.admin.id}/')
        self.assertEqual(resp2.status_code, 400)

    # ---- 未认证 ----
    def test_unauthenticated_denied(self):
        resp = self.client.get('/api/users/')
        self.assertEqual(resp.status_code, 401)
