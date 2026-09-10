import os
import json
import shutil

from django.db import models
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from django.conf import settings
from django.http import HttpResponse

from apps.common.utils import get_request_tenant, ok, fail
from apps.common.rbac import RoleRequiredMixin, ROLE_ADMIN, ROLE_EDITOR
from apps.knowledge.models import KnowledgeBase, Document, Paragraph, DocumentVersion
from apps.knowledge.serializers import (
    KnowledgeBaseSerializer, DocumentSerializer, ParagraphSerializer
)
from apps.knowledge.search import hybrid_search
from apps.knowledge.tasks import process_document


class KnowledgeBaseViewSet(RoleRequiredMixin, viewsets.ModelViewSet):
    write_roles = (ROLE_ADMIN, ROLE_EDITOR)
    serializer_class = KnowledgeBaseSerializer

    def get_queryset(self):
        tenant = get_request_tenant(self.request)
        qs = KnowledgeBase.objects.all()
        if tenant:
            qs = qs.filter(tenant=tenant)
        user = self.request.user
        if user.is_authenticated and user.role != ROLE_ADMIN:
            qs = qs.filter(
                models.Q(authorized_users__isnull=True) | models.Q(authorized_users=user)
            ).distinct()
        return qs.order_by('-create_time')

    def get_serializer_context(self):
        return {'request': self.request}

    @action(detail=True, methods=['get'])
    def documents(self, request, pk=None):
        kb = self.get_object()
        docs = kb.docs.all().order_by('-create_time')
        return ok(DocumentSerializer(docs, many=True).data)

    @action(detail=True, methods=['post'])
    def upload(self, request, pk=None):
        self._check_role()
        kb = self.get_object()
        file = request.FILES.get('file')
        if not file:
            return fail('缺少文件', code=400)
        if file.size > settings.MAX_UPLOAD_SIZE:
            return fail('文件过大', code=400)

        # 检查是否已存在同名文档，存在则创建新版本
        existing = Document.objects.filter(kb=kb, name=file.name).first()
        if existing:
            doc = existing
            doc.current_version = doc.current_version + 1
            doc.status = 'pending'
            doc.error_msg = ''
            doc.save(update_fields=['current_version', 'status', 'error_msg'])
        else:
            doc = Document.objects.create(kb=kb, name=file.name, source_type='file', current_version=1)

        upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads', str(doc.id))
        os.makedirs(upload_dir, exist_ok=True)
        save_path = os.path.join(upload_dir, file.name)
        with open(save_path, 'wb+') as f:
            for chunk in file.chunks():
                f.write(chunk)
        doc.file_path = save_path
        doc.save(update_fields=['file_path'])

        # 创建版本记录
        version = DocumentVersion.objects.create(
            document=doc, version=doc.current_version, file_path=save_path,
            uploader=request.user, is_current=True,
        )
        # 取消其他版本的当前标记
        DocumentVersion.objects.filter(document=doc).exclude(pk=version.pk).update(is_current=False)

        process_document.delay(doc.id)
        return ok(DocumentSerializer(doc).data,
                  message=f'已加入解析队列（版本 v{doc.current_version}）')

    @action(detail=True, methods=['get'])
    def export(self, request, pk=None):
        kb = self.get_object()
        docs = kb.docs.all().order_by('create_time')
        data = {
            'version': '1.0',
            'knowledge_base': {'name': kb.name, 'desc': kb.desc},
            'documents': [{
                'name': d.name, 'source_type': d.source_type, 'status': d.status,
                'char_count': d.char_count, 'paragraph_count': d.paragraphs.count(),
            } for d in docs],
        }
        response = HttpResponse(json.dumps(data, ensure_ascii=False, indent=2),
                                content_type='application/json')
        response['Content-Disposition'] = f'attachment; filename="kb_{kb.id}_export.json"'
        return response

    @action(detail=False, methods=['post'])
    def import_kb(self, request):
        self._check_role()
        name = request.data.get('name') or '导入的知识库'
        desc = request.data.get('desc', '')
        documents = request.data.get('documents', [])
        if not isinstance(documents, list):
            return fail('documents 必须是数组', code=400)
        tenant = get_request_tenant(request)
        kb = KnowledgeBase.objects.create(name=name, desc=desc, tenant=tenant)
        created_docs = []
        for d in documents:
            if not isinstance(d, dict) or not d.get('name'):
                continue
            doc = Document.objects.create(
                kb=kb, name=d['name'], source_type=d.get('source_type', 'file'),
                status='pending', char_count=d.get('char_count', 0),
            )
            created_docs.append({'id': doc.id, 'name': doc.name})
        return ok({'kb_id': kb.id, 'name': kb.name, 'documents_created': len(created_docs),
                   'documents': created_docs}, message='知识库导入成功，文档需重新上传文件后解析')

    @action(detail=True, methods=['get'])
    def authorized_users(self, request, pk=None):
        kb = self.get_object()
        users = kb.authorized_users.all()
        return ok([{'id': u.id, 'username': u.username, 'nickname': u.nickname, 'role': u.role} for u in users])

    @action(detail=True, methods=['post'])
    def grant_access(self, request, pk=None):
        self._check_role()
        kb = self.get_object()
        user_ids = request.data.get('user_ids', [])
        if not isinstance(user_ids, list) or not user_ids:
            return fail('user_ids 必须是非空数组', code=400)
        from apps.users.models import User
        users = User.objects.filter(pk__in=user_ids, tenant=kb.tenant)
        kb.authorized_users.add(*users)
        return ok({'granted': users.count(), 'total': kb.authorized_users.count()}, message='授权成功')

    @action(detail=True, methods=['post'])
    def revoke_access(self, request, pk=None):
        self._check_role()
        kb = self.get_object()
        user_ids = request.data.get('user_ids', [])
        if not isinstance(user_ids, list) or not user_ids:
            return fail('user_ids 必须是非空数组', code=400)
        from apps.users.models import User
        users = User.objects.filter(pk__in=user_ids)
        kb.authorized_users.remove(*users)
        return ok({'revoked': users.count(), 'total': kb.authorized_users.count()}, message='已取消授权')

    @action(detail=True, methods=['post'])
    def set_public(self, request, pk=None):
        self._check_role()
        kb = self.get_object()
        kb.authorized_users.clear()
        return ok({'is_public': True}, message='已设为公开')


class DocumentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DocumentSerializer

    def get_queryset(self):
        tenant = get_request_tenant(self.request)
        qs = Document.objects.all()
        if tenant:
            qs = qs.filter(kb__tenant=tenant)
        kb_id = self.request.query_params.get('kb_id')
        if kb_id:
            qs = qs.filter(kb_id=kb_id)
        user = self.request.user
        if user.is_authenticated and user.role != ROLE_ADMIN:
            qs = qs.filter(
                models.Q(authorized_users__isnull=True) | models.Q(authorized_users=user)
            ).distinct()
        return qs.order_by('-create_time')

    @action(detail=True, methods=['get'])
    def paragraphs(self, request, pk=None):
        doc = self.get_object()
        try:
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 50))
        except (TypeError, ValueError):
            page, page_size = 1, 50
        page = max(1, page)
        page_size = min(max(1, page_size), 200)
        qs = doc.paragraphs.all()
        total = qs.count()
        start = (page - 1) * page_size
        items = qs[start:start + page_size]
        return ok({'count': total, 'page': page, 'page_size': page_size,
                   'results': ParagraphSerializer(items, many=True).data})

    @action(detail=True, methods=['post'])
    def reparse(self, request, pk=None):
        if request.user.role not in (ROLE_ADMIN, ROLE_EDITOR):
            return fail('无权限：仅管理员或知识库维护可重新解析', code=403)
        doc = self.get_object()
        if doc.status == 'parsing':
            return fail('文档正在解析中，请稍候', code=400)
        doc.paragraphs.all().delete()
        doc.status = 'pending'
        doc.error_msg = ''
        doc.char_count = 0
        doc.save(update_fields=['status', 'error_msg', 'char_count'])
        process_document.delay(doc.id)
        return ok(DocumentSerializer(doc).data, message='已重新加入解析队列')

    # ---- 文档版本管理 ----
    @action(detail=True, methods=['get'])
    def versions(self, request, pk=None):
        """获取文档版本历史。"""
        doc = self.get_object()
        versions = doc.versions.all().order_by('-version')
        return ok([{
            'id': v.id, 'version': v.version, 'char_count': v.char_count,
            'remark': v.remark, 'is_current': v.is_current,
            'uploader': v.uploader.username if v.uploader else '',
            'create_time': v.create_time.strftime('%Y-%m-%d %H:%M:%S'),
        } for v in versions])

    @action(detail=True, methods=['post'])
    def rollback(self, request, pk=None):
        """回滚到指定版本。body: {version_id}
        将指定版本的文件复制为当前版本，重新解析。"""
        if request.user.role not in (ROLE_ADMIN, ROLE_EDITOR):
            return fail('无权限', code=403)
        doc = self.get_object()
        version_id = request.data.get('version_id')
        if not version_id:
            return fail('version_id 必填', code=400)
        try:
            target_version = DocumentVersion.objects.get(pk=version_id, document=doc)
        except DocumentVersion.DoesNotExist:
            return fail('版本不存在', code=404)

        # 复制历史版本文件为新版本
        new_version_num = doc.current_version + 1
        upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads', str(doc.id))
        os.makedirs(upload_dir, exist_ok=True)
        new_file_path = os.path.join(upload_dir, f'v{new_version_num}_{doc.name}')
        try:
            shutil.copy2(target_version.file_path, new_file_path)
        except Exception as e:
            return fail(f'文件复制失败: {str(e)}', code=500)

        doc.current_version = new_version_num
        doc.file_path = new_file_path
        doc.status = 'pending'
        doc.error_msg = ''
        doc.save(update_fields=['current_version', 'file_path', 'status', 'error_msg'])

        # 创建新版本记录
        new_ver = DocumentVersion.objects.create(
            document=doc, version=new_version_num, file_path=new_file_path,
            uploader=request.user, is_current=True,
            remark=f'回滚自 v{target_version.version}',
        )
        DocumentVersion.objects.filter(document=doc).exclude(pk=new_ver.pk).update(is_current=False)

        # 清除旧分段，重新解析
        doc.paragraphs.all().delete()
        process_document.delay(doc.id)
        return ok(DocumentSerializer(doc).data,
                  message=f'已回滚到 v{target_version.version}（创建新版本 v{new_version_num}）')

    # ---- 文档级权限管理 ----
    @action(detail=True, methods=['get'])
    def authorized_users(self, request, pk=None):
        doc = self.get_object()
        users = doc.authorized_users.all()
        return ok([{'id': u.id, 'username': u.username, 'nickname': u.nickname, 'role': u.role} for u in users])

    @action(detail=True, methods=['post'])
    def grant_access(self, request, pk=None):
        if request.user.role not in (ROLE_ADMIN, ROLE_EDITOR):
            return fail('无权限', code=403)
        doc = self.get_object()
        user_ids = request.data.get('user_ids', [])
        if not isinstance(user_ids, list) or not user_ids:
            return fail('user_ids 必须是非空数组', code=400)
        from apps.users.models import User
        users = User.objects.filter(pk__in=user_ids, tenant=doc.kb.tenant)
        doc.authorized_users.add(*users)
        return ok({'granted': users.count(), 'total': doc.authorized_users.count()}, message='授权成功')

    @action(detail=True, methods=['post'])
    def revoke_access(self, request, pk=None):
        if request.user.role not in (ROLE_ADMIN, ROLE_EDITOR):
            return fail('无权限', code=403)
        doc = self.get_object()
        user_ids = request.data.get('user_ids', [])
        if not isinstance(user_ids, list) or not user_ids:
            return fail('user_ids 必须是非空数组', code=400)
        from apps.users.models import User
        users = User.objects.filter(pk__in=user_ids)
        doc.authorized_users.remove(*users)
        return ok({'revoked': users.count(), 'total': doc.authorized_users.count()}, message='已取消授权')

    @action(detail=True, methods=['post'])
    def inherit_kb_access(self, request, pk=None):
        if request.user.role not in (ROLE_ADMIN, ROLE_EDITOR):
            return fail('无权限', code=403)
        doc = self.get_object()
        doc.authorized_users.clear()
        return ok({'inherit_kb': True}, message='已恢复继承知识库权限')


@api_view(['POST'])
def search_view(request):
    kb_id = request.data.get('kb_id')
    query = request.data.get('query', '').strip()
    top_k = int(request.data.get('top_k', 5))
    vector_weight = float(request.data.get('vector_weight', 0.7))
    vector_weight = max(0.0, min(1.0, vector_weight))
    if not kb_id or not query:
        return fail('kb_id 与 query 必填', code=400)
    try:
        kb = KnowledgeBase.objects.get(id=kb_id)
    except KnowledgeBase.DoesNotExist:
        return fail('知识库不存在', code=404)
    tenant = get_request_tenant(request)
    if tenant and kb.tenant_id != tenant.id:
        return fail('无权限', code=403)
    results = hybrid_search(kb, query, top_k=top_k, vector_weight=vector_weight)
    data = [{'content': r['paragraph'].content, 'score': r['score'],
             'doc_name': r['doc_name'], 'page_no': r['page_no']} for r in results]
    for r in results:
        r['paragraph'].hit_count += 1
        r['paragraph'].save(update_fields=['hit_count'])
    return ok(data)
