import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from .factories import ChiefFactory, UserFactory


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def chief(db):
    return ChiefFactory()


@pytest.fixture
def member(db):
    return UserFactory()


def auth_client(user):
    client = APIClient()
    token = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
    return client


@pytest.fixture
def chief_client(chief):
    return auth_client(chief)


@pytest.fixture
def member_client(member):
    return auth_client(member)