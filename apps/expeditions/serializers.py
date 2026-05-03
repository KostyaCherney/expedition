from rest_framework import serializers

from apps.users.serializers import UserSerializer
from .models import Expedition, ExpeditionMember


class ExpeditionMemberSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = ExpeditionMember
        fields = ('id', 'user', 'state', 'invited_at', 'confirmed_at')


class ExpeditionSerializer(serializers.ModelSerializer):
    chief = UserSerializer(read_only=True)
    members = ExpeditionMemberSerializer(many=True, read_only=True)

    class Meta:
        model = Expedition
        fields = (
            'id', 'title', 'description', 'status',
            'start_at', 'end_at', 'capacity',
            'chief', 'members',
            'created_at', 'updated_at',
        )
        read_only_fields = ('status', 'chief', 'created_at', 'updated_at')


class ExpeditionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expedition
        fields = ('title', 'description', 'start_at', 'end_at', 'capacity')

    def create(self, validated_data):
        validated_data['chief'] = self.context['request'].user
        return super().create(validated_data)


class InviteMemberSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
