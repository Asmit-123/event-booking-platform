from .models import Registration


def attendee_registrations(attendee):
    """An attendee's registrations as (upcoming, earlier) lists, using one query.

    Upcoming: active events that have not started, soonest first.
    Earlier: cancelled or already started events, most recent first.
    """
    registrations = list(
        Registration.objects.filter(attendee=attendee)
        .select_related("event__organizer")
        .order_by("event__start_datetime", "pk")
    )
    upcoming = [r for r in registrations if not r.event.is_cancelled and not r.event.is_past]
    earlier = [r for r in registrations if r.event.is_cancelled or r.event.is_past]
    earlier.reverse()
    return upcoming, earlier