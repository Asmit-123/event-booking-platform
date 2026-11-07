from django.conf import settings
from django.db import models


class Registration(models.Model):
    """One attendee holding one seat at one event."""

    event = models.ForeignKey(
        "events.Event",
        on_delete=models.PROTECT,
        related_name="registrations",
    )
    attendee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="registrations",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["event", "attendee"],
                name="unique_registration_per_event_attendee",
            ),
        ]

    def __str__(self):
        return f"{self.attendee} -> {self.event}"