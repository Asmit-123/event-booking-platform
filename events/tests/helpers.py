from datetime import timedelta

from django.utils import timezone

from accounts.models import User
from accounts.tests.helpers import create_user
from events.models import Event
from registrations.models import Registration


def make_organizer(name="organizer"):
    return create_user(User.Role.ORGANIZER, email=f"{name}@example.com", username=name)


def make_attendee(name="attendee"):
    return create_user(User.Role.ATTENDEE, email=f"{name}@example.com", username=name)


def event_fields(**overrides):
    """Valid event data as the service expects it (made-up values)."""
    fields = {
        "title": "Sample event",
        "description": "A made-up event for tests.",
        "venue": "Main hall",
        "start_datetime": timezone.now() + timedelta(days=7),
        "seat_limit": 10,
    }
    fields.update(overrides)
    return fields


def event_form_data(**overrides):
    """The same event as a browser would POST it."""
    start = timezone.localtime() + timedelta(days=7)
    data = {
        "title": "Sample event",
        "description": "A made-up event for tests.",
        "venue": "Main hall",
        "start_datetime": start.strftime("%Y-%m-%dT%H:%M"),
        "seat_limit": 10,
    }
    data.update(overrides)
    return data


def make_event(organizer, **overrides):
    """Create an event directly, bypassing the service (so tests can build past events)."""
    return Event.objects.create(organizer=organizer, **event_fields(**overrides))


def register(event, attendee):
    return Registration.objects.create(event=event, attendee=attendee)