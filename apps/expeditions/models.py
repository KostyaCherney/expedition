from django.conf import settings
from django.db import models


class Expedition(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        READY = 'ready', 'Ready'
        ACTIVE = 'active', 'Active'
        FINISHED = 'finished', 'Finished'

    ALLOWED_TRANSITIONS = {
        Status.DRAFT: Status.READY,
        Status.READY: Status.ACTIVE,
        Status.ACTIVE: Status.FINISHED,
    }

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    start_at = models.DateTimeField()
    end_at = models.DateTimeField(blank=True, null=True)
    capacity = models.PositiveIntegerField()
    chief = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='led_expeditions',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'expeditions'

    def __str__(self):
        return self.title


class ExpeditionMember(models.Model):
    class State(models.TextChoices):
        INVITED = 'invited', 'Invited'
        CONFIRMED = 'confirmed', 'Confirmed'

    expedition = models.ForeignKey(
        Expedition,
        on_delete=models.CASCADE,
        related_name='members',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='expedition_memberships',
    )
    state = models.CharField(max_length=10, choices=State.choices, default=State.INVITED)
    invited_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'expedition_members'
        unique_together = ('expedition', 'user')

    def __str__(self):
        return f'{self.user} in {self.expedition} ({self.state})'
