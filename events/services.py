from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from .models import Event
from .validators import validate_start_in_future


def create_event(organizer, *, title, description, venue, start_datetime, seat_limit):
    """Create an event owned by the given organizer, enforcing the business rules."""
    if not organizer.is_organizer:
        raise PermissionDenied("Only organizers can create events.")

    validate_start_in_future(start_datetime)

    event = Event(
        organizer=organizer,
        title=title,
        description=description,
        venue=venue,
        start_datetime=start_datetime,
        seat_limit=seat_limit,
    )
    event.full_clean()
    event.save()
    return event


@transaction.atomic
def update_event(organizer, event_id, *, title, description, venue, start_datetime, seat_limit):
    """Update an event, enforcing ownership, date and capacity rules under a row lock."""
    event = Event.objects.select_for_update().get(pk=event_id)

    if event.organizer_id != organizer.pk:
        raise PermissionDenied("You can only edit your own events.")
    if event.is_cancelled:
        raise ValidationError("A cancelled event cannot be edited.")
    if event.is_past:
        raise ValidationError("A past event cannot be edited.")

    validate_start_in_future(start_datetime)

    registered = event.registrations.count()
    if seat_limit < registered:
        raise ValidationError(
            {
                "seat_limit": (
                    f"The seat limit cannot be lower than the {registered} "
                    "people already registered."
                )
            }
        )

    event.title = title
    event.description = description
    event.venue = venue
    event.start_datetime = start_datetime
    event.seat_limit = seat_limit
    event.full_clean()
    event.save()
    return event

@transaction.atomic
def cancel_event(organizer, event_id):
    """Cancel an upcoming event owned by the organizer, keeping its registrations."""
    event = Event.objects.select_for_update().get(pk=event_id)

    if event.organizer_id != organizer.pk:
        raise PermissionDenied("You can only cancel your own events.")
    if event.is_cancelled:
        raise ValidationError("This event is already cancelled.")
    if event.is_past:
        raise ValidationError("A past event cannot be cancelled.")

    event.status = Event.Status.CANCELLED
    event.save(update_fields=["status", "updated_at"])
    return event