from rest_framework import serializers

from apps.chat.models import ChatMessage


class ChatRequestSerializer(serializers.Serializer):
    app_id = serializers.IntegerField(required=True)
    query = serializers.CharField(required=True)
    session_id = serializers.CharField(required=False, allow_blank=True)


class ChatHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ('id', 'session_id', 'role', 'content', 'feedback', 'feedback_comment', 'create_time')


class SessionSummarySerializer(serializers.Serializer):
    """会话列表项：按 session_id 聚合的摘要信息"""
    session_id = serializers.CharField()
    app_id = serializers.IntegerField(allow_null=True)
    app_name = serializers.CharField()
    msg_count = serializers.IntegerField()
    last_content = serializers.CharField()
    last_time = serializers.DateTimeField()
