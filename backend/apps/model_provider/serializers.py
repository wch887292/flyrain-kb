from rest_framework import serializers

from apps.model_provider.models import ModelProvider


class ModelProviderSerializer(serializers.ModelSerializer):
    api_key = serializers.CharField(write_only=True, required=False, allow_blank=True)
    api_key_masked = serializers.SerializerMethodField()

    class Meta:
        model = ModelProvider
        fields = ('id', 'name', 'type', 'base_url', 'api_key', 'api_key_masked',
                  'model_name', 'dimensions', 'is_default', 'create_time')
        read_only_fields = ('id', 'create_time')

    def get_api_key_masked(self, obj):
        """返回掩码后的 API Key，如 sk-abc...xyz"""
        if not obj.api_key:
            return ''
        if len(obj.api_key) <= 10:
            return '*' * len(obj.api_key)
        return f"{obj.api_key[:6]}...{obj.api_key[-4:]}"

    def validate(self, attrs):
        # 设为默认时取消同类型其它默认
        if attrs.get('is_default'):
            ModelProvider.objects.filter(
                type=attrs.get('type'), is_default=True
            ).update(is_default=False)
        return attrs

    def update(self, instance, validated_data):
        # 编辑时若 api_key 为空则不更新
        api_key = validated_data.pop('api_key', None)
        instance = super().update(instance, validated_data)
        if api_key:
            instance.api_key = api_key
            instance.save(update_fields=['api_key'])
        return instance


class ModelTestSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=['llm', 'embedding'])
    base_url = serializers.CharField()
    api_key = serializers.CharField()
    model_name = serializers.CharField()
