import pytest
from django.urls import reverse

from apps.expeditions.models import Expedition, ExpeditionMember
from .factories import ChiefFactory, ExpeditionFactory, ExpeditionMemberFactory, UserFactory
from .conftest import auth_client


@pytest.mark.django_db
class TestAuthEndpoints:
    def test_register(self, api_client):
        resp = api_client.post('/api/auth/register/', {
            'email': 'new@example.com',
            'name': 'New User',
            'role': 'member',
            'password': 'password123',
        })
        assert resp.status_code == 201

    def test_login(self, api_client, member):
        resp = api_client.post('/api/auth/login/', {
            'email': member.email,
            'password': 'password123',
        })
        assert resp.status_code == 200
        assert 'access' in resp.data

    def test_me(self, member_client, member):
        resp = member_client.get('/api/auth/me/')
        assert resp.status_code == 200
        assert resp.data['email'] == member.email


@pytest.mark.django_db
class TestExpeditionCRUD:
    def test_create_expedition(self, chief_client, chief):
        resp = chief_client.post('/api/expeditions/', {
            'title': 'Test Expedition',
            'start_at': '2025-01-01T10:00:00Z',
            'capacity': 5,
        })
        assert resp.status_code == 201
        assert resp.data['status'] == 'draft'

    def test_member_cannot_create_expedition(self, member_client):
        resp = member_client.post('/api/expeditions/', {
            'title': 'Test Expedition',
            'start_at': '2025-01-01T10:00:00Z',
            'capacity': 5,
        })
        assert resp.status_code == 403

    def test_list_only_own_expeditions(self, chief_client, chief, db):
        ExpeditionFactory(chief=chief)
        ExpeditionFactory()  # other chief's expedition

        resp = chief_client.get('/api/expeditions/')
        assert resp.status_code == 200
        assert len(resp.data) == 1


@pytest.mark.django_db
class TestInviteAndConfirm:
    def test_invite_member(self, mocker, chief_client, chief):
        mocker.patch('apps.expeditions.services._emit_expedition_event')
        exp = ExpeditionFactory(chief=chief)
        member = UserFactory()

        resp = chief_client.post(f'/api/expeditions/{exp.pk}/invite/', {'user_id': member.pk})
        assert resp.status_code == 201

    def test_confirm_participation(self, mocker, chief, member):
        mocker.patch('apps.expeditions.services._emit_expedition_event')
        exp = ExpeditionFactory(chief=chief)
        em = ExpeditionMemberFactory(expedition=exp, user=member, state=ExpeditionMember.State.INVITED)

        client = auth_client(member)
        resp = client.post(f'/api/expeditions/{exp.pk}/confirm/')
        assert resp.status_code == 200

        em.refresh_from_db()
        assert em.state == ExpeditionMember.State.CONFIRMED


@pytest.mark.django_db
class TestStatusTransitionAPI:
    def test_set_ready(self, mocker, chief_client, chief):
        mocker.patch('apps.expeditions.services._emit_expedition_event')
        exp = ExpeditionFactory(chief=chief, status=Expedition.Status.DRAFT)

        resp = chief_client.post(f'/api/expeditions/{exp.pk}/set-ready/')
        assert resp.status_code == 200
        assert resp.data['status'] == 'ready'

    def test_member_cannot_set_ready(self, mocker, member_client, chief):
        mocker.patch('apps.expeditions.services._emit_expedition_event')
        exp = ExpeditionFactory(chief=chief, status=Expedition.Status.DRAFT)
        # member is not part of this expedition, so 404
        resp = member_client.post(f'/api/expeditions/{exp.pk}/set-ready/')
        assert resp.status_code == 404