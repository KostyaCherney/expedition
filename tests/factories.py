import factory
from django.utils import timezone

from apps.users.models import User
from apps.expeditions.models import Expedition, ExpeditionMember


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f'user{n}@example.com')
    name = factory.Sequence(lambda n: f'User {n}')
    role = User.Role.MEMBER
    password = factory.PostGenerationMethodCall('set_password', 'password123')


class ChiefFactory(UserFactory):
    role = User.Role.CHIEF


class ExpeditionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Expedition

    title = factory.Sequence(lambda n: f'Expedition {n}')
    status = Expedition.Status.DRAFT
    start_at = factory.LazyFunction(timezone.now)
    capacity = 10
    chief = factory.SubFactory(ChiefFactory)


class ExpeditionMemberFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ExpeditionMember

    expedition = factory.SubFactory(ExpeditionFactory)
    user = factory.SubFactory(UserFactory)
    state = ExpeditionMember.State.INVITED