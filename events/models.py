from django.conf import settings
from django.core.validators import MaxLengthValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

DESCRIPTION_MAX_LENGTH = 5000

class Event(models.Model):
    """An event published by an organizer, with a fixed number of seats."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        CANCELLED = "cancelled", "Cancelled"

    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="organized_events",
    )
    title = models.CharField(max_length=200)
    description = models.TextField(
        max_length=DESCRIPTION_MAX_LENGTH,
        validators=[MaxLengthValidator(DESCRIPTION_MAX_LENGTH)],
    )
    venue = models.CharField(max_length=255)
    start_datetime = models.DateTimeField()
    seat_limit = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["start_datetime"]
        constraints = [
            models.CheckConstraint(
                condition=Q(seat_limit__gt=0),
                name="event_seat_limit_positive",
            ),
        ]
        indexes = [
            models.Index(
                fields=["status", "start_datetime"],
                name="event_status_start_idx",
            ),
        ]

    @property
    def is_cancelled(self):
        return self.status == self.Status.CANCELLED

    @property
    def is_past(self):
        return self.start_datetime <= timezone.now()
    
    @property
    def is_editable(self):
        return not self.is_cancelled and not self.is_past

    def __str__(self):
        return self.title