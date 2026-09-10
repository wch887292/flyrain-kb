from rest_framework import serializers

from apps.application.models import Application, Workflow, WorkflowStep, WorkflowExecution, Plugin
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
                  'temperature', 'max_tokens', 'vector_weight', 'is_active', 'create_time')
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


class PluginSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plugin
        fields = ('id', 'name', 'type', 'description', 'config', 'is_active', 'create_time')
        read_only_fields = ('id', 'create_time')


class WorkflowStepSerializer(serializers.ModelSerializer):
    plugin_name = serializers.CharField(source='plugin.name', read_only=True)

    class Meta:
        model = WorkflowStep
        fields = ('id', 'workflow', 'order', 'name', 'step_type', 'plugin', 'plugin_name',
                  'prompt', 'temperature', 'max_tokens', 'create_time')
        read_only_fields = ('id', 'workflow', 'create_time', 'plugin_name')


class WorkflowSerializer(serializers.ModelSerializer):
    steps = WorkflowStepSerializer(many=True, read_only=True)
    step_count = serializers.SerializerMethodField()

    class Meta:
        model = Workflow
        fields = ('id', 'name', 'desc', 'status', 'steps', 'step_count', 'create_time', 'update_time')
        read_only_fields = ('id', 'steps', 'step_count', 'create_time', 'update_time')

    def get_step_count(self, obj):
        return obj.steps.count()

    def create(self, validated_data):
        tenant = get_request_tenant(self.context['request'])
        return Workflow.objects.create(tenant=tenant, **validated_data)


class WorkflowExecutionSerializer(serializers.ModelSerializer):
    workflow_name = serializers.CharField(source='workflow.name', read_only=True)

    class Meta:
        model = WorkflowExecution
        fields = ('id', 'workflow', 'workflow_name', 'input_text', 'output_text',
                  'step_outputs', 'status', 'error_msg', 'duration_ms', 'create_time')
        read_only_fields = ('id', 'workflow_name', 'output_text', 'step_outputs',
                            'status', 'error_msg', 'duration_ms', 'create_time')
