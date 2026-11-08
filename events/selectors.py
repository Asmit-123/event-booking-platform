from django.db.models import Count, F
from django.utils import timezone

from .models import Event


def organizer_events(organizer):
    """Events created by this organizer, latest start first, with seats taken."""
    return (
        Event.objects.filter(organizer=organizer)
        .annotate(seats_taken=Count("registrations"))
        .order_by("-start_datetime")
    )


def event_registrations(event):
    """Registrations for an event, earliest first, with attendee data loaded."""
    return event.registrations.select_related("attendee").order_by("created_at")


def events_with_seats():
    """All events with the organizer loaded and seats taken and left computed."""
    return (
        Event.objects.select_related("organizer")
        .annotate(seats_taken=Count("registrations"))
        .annotate(seats_left=F("seat_limit") - F("seats_taken"))
    )


def upcoming_events():
    """Active events that have not started yet, soonest first."""
    return (
        events_with_seats()
        .filter(status=Event.Status.ACTIVE, start_datetime__gt=timezone.now())
        .order_by("start_datetime", "pk")
    )