from rest_framework import serializers

from apps.application.models import Application
from apps.knowledge.models import KnowledgeBase
from apps.common.utils import get_request_tenant


class ApplicationSerializer(serializers.ModelSerializer):
    kb_ids = serializers.PrimaryKeyRelatedField(
        queryset=KnowledgeBase.objects.all(), source='kbs',
        many=True, write_only=True, required=False
    )
    kb_names = serializers.SerializerMethodField()

    class Meta:
        model = Application
        fields = ('id', 'name', 'desc', 'kb_ids', 'kb_names', 'system_prompt',
                  'temperature', 'max_tokens', 'is_active', 'create_time')
        read_only_fields = ('id', 'kb_names', 'create_time')

    def get_kb_names(self, obj):
        return [kb.name for kb in obj.kbs.all()]

    def create(self, validated_data):
        kbs = validated_data.pop('kbs', [])
        tenant = get_request_tenant(self.context['request'])
        app = Application.objects.create(tenant=tenant, **validated_data)
        if kbs:
            app.kbs.set(kbs)
        return app

    def update(self, instance, validated_data):
        kbs = validated_data.pop('kbs', None)
        for k, v in validated_data.items():
            setattr(instance, k, v)
        instance.save()
        if kbs is not None:
            instance.kbs.set(kbs)
        return instance
