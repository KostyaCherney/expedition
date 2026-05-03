from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.utils import timezone

from .models import Expedition, ExpeditionMember


def _emit_expedition_event(expedition_id: int, event_type: str, payload: dict) -> None:
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'expedition_{expedition_id}',
        {'type': 'expedition.event', 'event_type': event_type, 'payload': payload},
    )


def invite_member(expedition: Expedition, user, invited_by) -> ExpeditionMember:
    from apps.users.models import User

    if user.role != User.Role.MEMBER:
        raise ValueError('Only users with role "member" can be invited.')

    with transaction.atomic():
        exp = Expedition.objects.select_for_update().get(pk=expedition.pk)

        if exp.status != Expedition.Status.DRAFT:
            raise ValueError('Members can only be invited while expedition is in draft.')

        member, created = ExpeditionMember.objects.get_or_create(
            expedition=exp,
            user=user,
        )
        if not created:
            raise ValueError('User is already invited to this expedition.')

    _emit_expedition_event(
        exp.pk,
        'member_invited',
        {'expedition_id': exp.pk, 'user_id': user.pk, 'user_name': user.name},
    )
    return member


def confirm_member(expedition: Expedition, user) -> ExpeditionMember:
    with transaction.atomic():
        member = (
            ExpeditionMember.objects
            .select_for_update()
            .get(expedition=expedition, user=user)
        )
        if member.state != ExpeditionMember.State.INVITED:
            raise ValueError('Only invited members can confirm participation.')

        member.state = ExpeditionMember.State.CONFIRMED
        member.confirmed_at = timezone.now()
        member.save(update_fields=['state', 'confirmed_at'])

    _emit_expedition_event(
        expedition.pk,
        'member_confirmed',
        {'expedition_id': expedition.pk, 'user_id': user.pk, 'user_name': user.name},
    )
    return member


def _transition_status(expedition_id: int, target_status: str) -> Expedition:
    with transaction.atomic():
        exp = Expedition.objects.select_for_update().get(pk=expedition_id)
        allowed_next = Expedition.ALLOWED_TRANSITIONS.get(exp.status)

        if allowed_next != target_status:
            raise ValueError(
                f'Cannot transition from "{exp.status}" to "{target_status}".'
            )

        if target_status == Expedition.Status.ACTIVE:
            _check_active_preconditions(exp)

        exp.status = target_status
        exp.save(update_fields=['status', 'updated_at'])

    _emit_expedition_event(
        exp.pk,
        'expedition_status',
        {'expedition_id': exp.pk, 'status': target_status},
    )
    return exp


def _check_active_preconditions(exp: Expedition) -> None:
    now = timezone.now()
    if exp.start_at > now:
        raise ValueError('start_at is in the future.')

    confirmed = list(
        ExpeditionMember.objects.filter(
            expedition=exp,
            state=ExpeditionMember.State.CONFIRMED,
        ).select_related('user')
    )
    confirmed_count = len(confirmed)

    if confirmed_count < 2:
        raise ValueError('At least 2 confirmed members are required.')

    if confirmed_count > exp.capacity:
        raise ValueError('Confirmed members exceed capacity.')

    # Check no confirmed member is in another active expedition
    confirmed_user_ids = [m.user_id for m in confirmed]
    conflict = (
        ExpeditionMember.objects
        .filter(
            user_id__in=confirmed_user_ids,
            state=ExpeditionMember.State.CONFIRMED,
            expedition__status=Expedition.Status.ACTIVE,
        )
        .exclude(expedition=exp)
        .exists()
    )
    if conflict:
        raise ValueError('One or more confirmed members are in another active expedition.')


def _chief_transition(expedition_id: int, chief, target_status: str) -> Expedition:
    exp = Expedition.objects.get(pk=expedition_id)
    if exp.chief_id != chief.pk:
        raise PermissionError('Only the chief can change expedition status.')
    return _transition_status(expedition_id, target_status)


def set_ready(expedition_id: int, chief) -> Expedition:
    return _chief_transition(expedition_id, chief, Expedition.Status.READY)


def set_active(expedition_id: int, chief) -> Expedition:
    return _chief_transition(expedition_id, chief, Expedition.Status.ACTIVE)


def set_finished(expedition_id: int, chief) -> Expedition:
    return _chief_transition(expedition_id, chief, Expedition.Status.FINISHED)
