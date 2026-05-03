import pytest
from django.utils import timezone

from apps.expeditions.models import Expedition, ExpeditionMember
from apps.expeditions import services
from .factories import ChiefFactory, ExpeditionFactory, ExpeditionMemberFactory, UserFactory


@pytest.mark.django_db
class TestInviteMember:
    def test_invite_member_success(self, mocker):
        mocker.patch('apps.expeditions.services._emit_expedition_event')
        chief = ChiefFactory()
        member = UserFactory()
        exp = ExpeditionFactory(chief=chief)

        em = services.invite_member(exp, member, invited_by=chief)

        assert em.state == ExpeditionMember.State.INVITED
        assert em.expedition == exp

    def test_cannot_invite_chief_role(self, mocker):
        mocker.patch('apps.expeditions.services._emit_expedition_event')
        chief = ChiefFactory()
        another_chief = ChiefFactory()
        exp = ExpeditionFactory(chief=chief)

        with pytest.raises(ValueError, match='role "member"'):
            services.invite_member(exp, another_chief, invited_by=chief)

    def test_cannot_invite_duplicate(self, mocker):
        mocker.patch('apps.expeditions.services._emit_expedition_event')
        chief = ChiefFactory()
        member = UserFactory()
        exp = ExpeditionFactory(chief=chief)
        services.invite_member(exp, member, invited_by=chief)

        with pytest.raises(ValueError, match='already invited'):
            services.invite_member(exp, member, invited_by=chief)


@pytest.mark.django_db
class TestConfirmMember:
    def test_confirm_success(self, mocker):
        mocker.patch('apps.expeditions.services._emit_expedition_event')
        em = ExpeditionMemberFactory(state=ExpeditionMember.State.INVITED)

        result = services.confirm_member(em.expedition, em.user)

        assert result.state == ExpeditionMember.State.CONFIRMED
        assert result.confirmed_at is not None

    def test_cannot_confirm_twice(self, mocker):
        mocker.patch('apps.expeditions.services._emit_expedition_event')
        em = ExpeditionMemberFactory(state=ExpeditionMember.State.CONFIRMED)

        with pytest.raises(ValueError, match='Only invited'):
            services.confirm_member(em.expedition, em.user)


@pytest.mark.django_db
class TestStatusTransitions:
    def _make_ready_expedition(self, mocker):
        mocker.patch('apps.expeditions.services._emit_expedition_event')
        chief = ChiefFactory()
        exp = ExpeditionFactory(chief=chief, status=Expedition.Status.DRAFT)
        services.set_ready(exp.pk, chief)
        exp.refresh_from_db()
        return exp, chief

    def test_draft_to_ready(self, mocker):
        mocker.patch('apps.expeditions.services._emit_expedition_event')
        chief = ChiefFactory()
        exp = ExpeditionFactory(chief=chief, status=Expedition.Status.DRAFT)

        result = services.set_ready(exp.pk, chief)

        assert result.status == Expedition.Status.READY

    def test_ready_to_active(self, mocker):
        mocker.patch('apps.expeditions.services._emit_expedition_event')
        exp, chief = self._make_ready_expedition(mocker)

        members = [ExpeditionMemberFactory(
            expedition=exp,
            state=ExpeditionMember.State.CONFIRMED,
        ) for _ in range(2)]

        exp.start_at = timezone.now()
        exp.save()

        result = services.set_active(exp.pk, chief)
        assert result.status == Expedition.Status.ACTIVE

    def test_active_to_finished(self, mocker):
        mocker.patch('apps.expeditions.services._emit_expedition_event')
        chief = ChiefFactory()
        exp = ExpeditionFactory(chief=chief, status=Expedition.Status.ACTIVE)

        result = services.set_finished(exp.pk, chief)
        assert result.status == Expedition.Status.FINISHED

    def test_invalid_transition(self, mocker):
        mocker.patch('apps.expeditions.services._emit_expedition_event')
        chief = ChiefFactory()
        exp = ExpeditionFactory(chief=chief, status=Expedition.Status.DRAFT)

        with pytest.raises(ValueError, match='Cannot transition'):
            services._transition_status(exp.pk, Expedition.Status.ACTIVE)

    def test_only_chief_can_set_ready(self, mocker):
        mocker.patch('apps.expeditions.services._emit_expedition_event')
        exp = ExpeditionFactory(status=Expedition.Status.DRAFT)
        other_chief = ChiefFactory()

        with pytest.raises(PermissionError):
            services.set_ready(exp.pk, other_chief)

    def test_active_fails_if_start_at_future(self, mocker):
        mocker.patch('apps.expeditions.services._emit_expedition_event')
        from django.utils import timezone
        import datetime
        chief = ChiefFactory()
        exp = ExpeditionFactory(
            chief=chief,
            status=Expedition.Status.READY,
            start_at=timezone.now() + datetime.timedelta(days=1),
        )
        for _ in range(2):
            ExpeditionMemberFactory(expedition=exp, state=ExpeditionMember.State.CONFIRMED)

        with pytest.raises(ValueError, match='future'):
            services.set_active(exp.pk, chief)

    def test_active_fails_if_member_in_other_active(self, mocker):
        mocker.patch('apps.expeditions.services._emit_expedition_event')
        chief = ChiefFactory()
        exp = ExpeditionFactory(
            chief=chief,
            status=Expedition.Status.READY,
            start_at=timezone.now(),
        )
        other_exp = ExpeditionFactory(status=Expedition.Status.ACTIVE)

        members = []
        for _ in range(2):
            m = ExpeditionMemberFactory(expedition=exp, state=ExpeditionMember.State.CONFIRMED)
            members.append(m)
            ExpeditionMemberFactory(
                expedition=other_exp, user=m.user,
                state=ExpeditionMember.State.CONFIRMED,
            )

        with pytest.raises(ValueError, match='another active expedition'):
            services.set_active(exp.pk, chief)