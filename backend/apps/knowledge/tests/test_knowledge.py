"""知识库 CRUD 与权限测试"""
from django.test import TestCase
from rest_framework.test import APIClient

from apps.users.models import User, Tenant
from apps.knowledge.models import KnowledgeBase
from apps.common.rbac import ROLE_ADMIN, ROLE_EDITOR, ROLE_USER


class TestKnowledgeBase(TestCase):
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

    def _auth(self, u):
        self.client.force_authenticate(user=u)

    def test_admin_can_create_kb(self):
        self._auth(self.admin)
        resp = self.client.post('/api/knowledge/bases/', {'name': '测试知识库', 'desc': 'desc'})
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(KnowledgeBase.objects.count(), 1)

    def test_editor_can_create_kb(self):
        self._auth(self.editor)
        resp = self.client.post('/api/knowledge/bases/', {'name': '编辑者知识库'})
        self.assertEqual(resp.status_code, 201)

    def test_user_cannot_create_kb(self):
        self._auth(self.user)
        resp = self.client.post('/api/knowledge/bases/', {'name': '用户尝试创建'})
        self.assertEqual(resp.status_code, 403)

    def test_user_can_view_kb_list(self):
        """普通用户可读知识库列表"""
        KnowledgeBase.objects.create(name="可见知识库", tenant=self.tenant)
        self._auth(self.user)
        resp = self.client.get('/api/knowledge/bases/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data['results']), 1)

    def test_user_cannot_delete_kb(self):
        kb = KnowledgeBase.objects.create(name="待删除", tenant=self.tenant)
        self._auth(self.user)
        resp = self.client.delete(f'/api/knowledge/bases/{kb.id}/')
        self.assertEqual(resp.status_code, 403)

    def test_editor_can_delete_kb(self):
        kb = KnowledgeBase.objects.create(name="编辑者删除", tenant=self.tenant)
        self._auth(self.editor)
        resp = self.client.delete(f'/api/knowledge/bases/{kb.id}/')
        self.assertEqual(resp.status_code, 204)

    def test_tenant_isolation(self):
        """不同租户的知识库互不可见"""
        other_tenant = Tenant.objects.create(name="其他租户")
        KnowledgeBase.objects.create(name="租户A知识库", tenant=self.tenant)
        KnowledgeBase.objects.create(name="租户B知识库", tenant=other_tenant)
        self._auth(self.admin)
        resp = self.client.get('/api/knowledge/bases/')
        self.assertEqual(resp.status_code, 200)
        # admin 属于 tenant，只能看到 tenant 的知识库
        names = [kb['name'] for kb in resp.data['results']]
        self.assertIn("租户A知识库", names)
        self.assertNotIn("租户B知识库", names)
