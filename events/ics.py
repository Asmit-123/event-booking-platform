from datetime import timedelta
from datetime import timezone as dt_timezone

from django.utils import timezone

DEFAULT_DURATION = timedelta(hours=1)  # events have a start time only


def _escape(text):
    """Escape a text value as RFC 5545 requires."""
    return (
        str(text)
        .replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
        .replace("\r", "\\n")
    )


def _fold(line):
    """Split a line so no physical line exceeds 75 bytes, never cutting a multibyte character."""
    raw = line.encode("utf-8")
    parts = []
    while len(raw) > 75:
        cut = 75
        while (raw[cut] & 0xC0) == 0x80:
            cut -= 1
        parts.append(raw[:cut])
        raw = b" " + raw[cut:]
    parts.append(raw)
    return b"\r\n".join(parts).decode("utf-8")


def _utc(moment):
    return moment.astimezone(dt_timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def build_ics(event, url):
    start = event.start_datetime
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Event Booking//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:event-{event.pk}@event-booking",
        f"DTSTAMP:{_utc(timezone.now())}",
        f"DTSTART:{_utc(start)}",
        f"DTEND:{_utc(start + DEFAULT_DURATION)}",
        f"SUMMARY:{_escape(event.title)}",
        f"LOCATION:{_escape(event.venue)}",
        f"DESCRIPTION:{_escape(event.description + chr(10) + chr(10) + url)}",
        f"URL:{url}",
        "END:VEVENT",
        "END:VCALENDAR",
    ]
    return "\r\n".join(_fold(line) for line in lines) + "\r\n"