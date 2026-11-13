from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from events.models import Event

from .models import Registration


@transaction.atomic
def register_for_event(attendee, event_id):
    """Give the attendee one seat at the event, enforcing every booking rule.

    The event row is locked first, so concurrent registrations (and edits or
    cancellations of the same event) are processed one at a time.
    """
    if not attendee.is_attendee:
        raise PermissionDenied("Only attendees can register for events.")

    event = Event.objects.select_for_update().get(pk=event_id)

    if event.is_cancelled:
        raise ValidationError("This event has been cancelled.")
    if event.is_past:
        raise ValidationError("Registration is closed: this event has already started.")
    if event.is_registration_closed:
        raise ValidationError("Registration for this event has closed.")
    if event.registrations.filter(attendee=attendee).exists():
        raise ValidationError("You are already registered for this event.")
    if event.registrations.count() >= event.seat_limit:
        raise ValidationError("Sorry, this event is fully booked.")

    return Registration.objects.create(event=event, attendee=attendee)
