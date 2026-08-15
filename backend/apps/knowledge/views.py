import os

from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from django.conf import settings

from apps.common.utils import get_request_tenant, ok, fail
from apps.common.rbac import RoleRequiredMixin, ROLE_ADMIN, ROLE_EDITOR
from apps.knowledge.models import KnowledgeBase, Document, Paragraph
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
        doc = Document.objects.create(kb=kb, name=file.name, source_type='file')
        upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads', str(doc.id))
        os.makedirs(upload_dir, exist_ok=True)
        save_path = os.path.join(upload_dir, file.name)
        with open(save_path, 'wb+') as f:
            for chunk in file.chunks():
                f.write(chunk)
        doc.file_path = save_path
        doc.save(update_fields=['file_path'])
        # 异步解析向量化
        process_document.delay(doc.id)
        return ok(DocumentSerializer(doc).data, message='已加入解析队列')


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
        return qs.order_by('-create_time')

    @action(detail=True, methods=['get'])
    def paragraphs(self, request, pk=None):
        """分段预览（真实数据，支持分页）。query: page, page_size"""
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
        return ok({
            'count': total,
            'page': page,
            'page_size': page_size,
            'results': ParagraphSerializer(items, many=True).data,
        })


@api_view(['POST'])
def search_view(request):
    """混合检索：body {kb_id, query, top_k?}"""
    kb_id = request.data.get('kb_id')
    query = request.data.get('query', '').strip()
    top_k = int(request.data.get('top_k', 5))
    if not kb_id or not query:
        return fail('kb_id 与 query 必填', code=400)
    try:
        kb = KnowledgeBase.objects.get(id=kb_id)
    except KnowledgeBase.DoesNotExist:
        return fail('知识库不存在', code=404)
    # 租户隔离校验
    tenant = get_request_tenant(request)
    if tenant and kb.tenant_id != tenant.id:
        return fail('无权限', code=403)
    results = hybrid_search(kb, query, top_k=top_k)
    data = [{
        'content': r['paragraph'].content,
        'score': r['score'],
        'doc_name': r['doc_name'],
        'page_no': r['page_no'],
    } for r in results]
    # 命中计数
    for r in results:
        r['paragraph'].hit_count += 1
        r['paragraph'].save(update_fields=['hit_count'])
    return ok(data)
