from django.db.models import Count

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