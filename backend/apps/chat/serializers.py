from rest_framework import serializers

from apps.chat.models import ChatMessage


class ChatRequestSerializer(serializers.Serializer):
    app_id = serializers.IntegerField(required=True)
    query = serializers.CharField(required=True)
    session_id = serializers.CharField(required=False, allow_blank=True)


class ChatHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ('id', 'session_id', 'role', 'content', 'create_time')
