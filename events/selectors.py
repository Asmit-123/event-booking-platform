from datetime import datetime, time, timedelta
from django.db.models import Count, F, Q
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
    
def search_events(queryset, term):
    """Narrow an event queryset to rows whose title, venue or description contain `term`.

    A blank term returns the queryset unchanged. icontains is a case-insensitive
    substring match (SQL: ILIKE '%term%'), and Django escapes %, _ and quotes for us.
    """
    term = (term or "").strip()
    if not term:
        return queryset
    return queryset.filter(
        Q(title__icontains=term)
        | Q(venue__icontains=term)
        | Q(description__icontains=term)
    )
    
def _start_of_day(day):
    """Midnight at the start of `day`, in the project's current time zone (Asia/Kolkata)."""
    return timezone.make_aware(datetime.combine(day, time.min))


def filter_by_date_range(queryset, date_from=None, date_to=None):
    """Keep events starting on or after `date_from` and on or before `date_to`.

    Both ends are whole local days and both are optional. The upper bound is
    "before midnight of the following day", so events late on `date_to` are kept.
    Comparing the raw start_datetime column (not __date) lets Postgres use its index.
    """
    if date_from:
        queryset = queryset.filter(start_datetime__gte=_start_of_day(date_from))
    if date_to:
        next_day = date_to + timedelta(days=1)
        queryset = queryset.filter(start_datetime__lt=_start_of_day(next_day))
    return queryset

def only_with_seats(queryset):
    """Keep events with at least one free seat (needs the seats_left annotation)."""
    return queryset.filter(seats_left__gt=0)

def summarize_organizer_events(events):
    """Dashboard numbers from an already-loaded list of events annotated with seats_taken.

    Cancelled events are left out of the registration and fill-rate figures.
    """
    live = [event for event in events if not event.is_cancelled]
    upcoming = [event for event in live if not event.is_past]
    seats_total = sum(event.seat_limit for event in live)
    seats_taken = sum(event.seats_taken for event in live)
    return {
        "total_events": len(events),
        "upcoming_events": len(upcoming),
        "cancelled_events": len(events) - len(live),
        "total_registrations": seats_taken,
        "fill_rate": round(100 * seats_taken / seats_total) if seats_total else 0,
    }