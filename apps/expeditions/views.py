from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from . import services
from .models import Expedition, ExpeditionMember
from .serializers import (
    ExpeditionCreateSerializer,
    ExpeditionSerializer,
    InviteMemberSerializer,
)

User = get_user_model()


class IsChiefUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.role == User.Role.CHIEF


class ExpeditionViewSet(ModelViewSet):
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        return (
            Expedition.objects
            .filter(chief=user) | Expedition.objects.filter(members__user=user)
        ).distinct().select_related('chief').prefetch_related('members__user')

    def get_serializer_class(self):
        if self.action == 'create':
            return ExpeditionCreateSerializer
        return ExpeditionSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if request.user.role != User.Role.CHIEF:
            raise PermissionDenied('Only chiefs can create expeditions.')
        expedition = serializer.save()
        return Response(
            ExpeditionSerializer(expedition, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )

    def _require_chief(self, expedition):
        if expedition.chief_id != self.request.user.pk:
            raise PermissionDenied('Only the chief of this expedition can perform this action.')

    @action(detail=True, methods=['post'], url_path='set-ready')
    def set_ready(self, request, pk=None):
        try:
            exp = services.set_ready(pk, request.user)
        except (ValueError, PermissionError) as e:
            raise ValidationError(str(e))
        return Response(ExpeditionSerializer(exp, context={'request': request}).data)

    @action(detail=True, methods=['post'], url_path='set-active')
    def set_active(self, request, pk=None):
        try:
            exp = services.set_active(pk, request.user)
        except (ValueError, PermissionError) as e:
            raise ValidationError(str(e))
        return Response(ExpeditionSerializer(exp, context={'request': request}).data)

    @action(detail=True, methods=['post'], url_path='set-finished')
    def set_finished(self, request, pk=None):
        try:
            exp = services.set_finished(pk, request.user)
        except (ValueError, PermissionError) as e:
            raise ValidationError(str(e))
        return Response(ExpeditionSerializer(exp, context={'request': request}).data)

    @action(detail=True, methods=['post'], url_path='invite')
    def invite(self, request, pk=None):
        expedition = self.get_object()
        self._require_chief(expedition)

        serializer = InviteMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = User.objects.get(pk=serializer.validated_data['user_id'])
        except User.DoesNotExist:
            raise ValidationError('User not found.')

        try:
            services.invite_member(expedition, user, invited_by=request.user)
        except ValueError as e:
            raise ValidationError(str(e))

        return Response({'detail': 'Invitation sent.'}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='confirm')
    def confirm(self, request, pk=None):
        expedition = self.get_object()
        try:
            services.confirm_member(expedition, request.user)
        except (ValueError, ExpeditionMember.DoesNotExist) as e:
            raise ValidationError(str(e))
        return Response({'detail': 'Participation confirmed.'})
