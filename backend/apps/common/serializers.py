from rest_framework import serializers

from apps.common.models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True, default='')
    action_display = serializers.CharField(source='get_action_display', read_only=True)

    class Meta:
        model = AuditLog
        fields = ('id', 'user', 'username', 'action', 'action_display',
                  'resource_type', 'resource_id', 'detail', 'ip', 'path',
                  'method', 'status_code', 'create_time')
        read_only_fields = fields
