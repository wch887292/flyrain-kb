from rest_framework import serializers

from apps.model_provider.models import ModelProvider


class ModelProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModelProvider
        fields = ('id', 'name', 'type', 'base_url', 'api_key', 'model_name',
                  'dimensions', 'is_default', 'create_time')
        read_only_fields = ('id', 'create_time')

    def validate(self, attrs):
        # 设为默认时取消同类型其它默认
        if attrs.get('is_default'):
            ModelProvider.objects.filter(
                type=attrs.get('type'), is_default=True
            ).update(is_default=False)
        return attrs


class ModelTestSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=['llm', 'embedding'])
    base_url = serializers.CharField()
    api_key = serializers.CharField()
    model_name = serializers.CharField()
