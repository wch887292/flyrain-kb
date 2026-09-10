from rest_framework import serializers

from apps.knowledge.models import KnowledgeBase, Document, Paragraph
from apps.common.utils import get_request_tenant


class KnowledgeBaseSerializer(serializers.ModelSerializer):
    doc_count = serializers.SerializerMethodField()
    tenant = serializers.CharField(source='tenant.name', read_only=True)

    class Meta:
        model = KnowledgeBase
        fields = ('id', 'name', 'desc', 'tenant', 'doc_count', 'create_time')
        read_only_fields = ('id', 'doc_count', 'tenant', 'create_time')

    def get_doc_count(self, obj):
        return obj.docs.count()

    def create(self, validated_data):
        tenant = get_request_tenant(self.context['request'])
        return KnowledgeBase.objects.create(tenant=tenant, **validated_data)


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ('id', 'kb', 'name', 'source_type', 'status', 'char_count',
                  'has_images', 'has_tables', 'image_count', 'table_count',
                  'error_msg', 'create_time')
        read_only_fields = ('id', 'status', 'char_count', 'has_images', 'has_tables',
                            'image_count', 'table_count', 'error_msg', 'create_time')


class ParagraphSerializer(serializers.ModelSerializer):
    doc_name = serializers.CharField(source='doc.name', read_only=True)

    class Meta:
        model = Paragraph
        fields = ('id', 'doc', 'doc_name', 'content', 'page_no', 'index', 'hit_count')
