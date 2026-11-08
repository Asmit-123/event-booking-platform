from django.core.exceptions import PermissionDenied

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