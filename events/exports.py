import csv

from django.utils import timezone

FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def csv_safe(value):
    """Stop spreadsheet apps from executing a cell as a formula (CSV injection)."""
    text = str(value)
    return "'" + text if text.startswith(FORMULA_PREFIXES) else text


def write_attendees_csv(response, registrations):
    response.write("\ufeff")  # byte-order mark so Excel reads UTF-8 names correctly
    writer = csv.writer(response)
    writer.writerow(["Name", "Email", "Registered at"])
    for registration in registrations:
        attendee = registration.attendee
        registered_at = timezone.localtime(registration.created_at).strftime("%Y-%m-%d %H:%M")
        writer.writerow([csv_safe(attendee.get_full_name()), csv_safe(attendee.email), registered_at])