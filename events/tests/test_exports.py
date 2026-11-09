from datetime import datetime, time, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from events.exports import csv_safe

from .helpers import make_attendee, make_event, make_organizer, register


class CsvExportTests(TestCase):
    def setUp(self):
        self.organizer = make_organizer()
        self.event = make_event(self.organizer)
        self.attendee = make_attendee("att1")
        register(self.event, self.attendee)
        self.url = reverse("events:event_attendees_csv", args=[self.event.pk])

    def test_owner_downloads_csv_with_attendee_rows(self):
        self.client.force_login(self.organizer)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response["Content-Type"])
        self.assertIn("attachment", response["Content-Disposition"])
        body = response.content.decode("utf-8-sig")
        self.assertIn("Name,Email,Registered at", body)
        self.assertIn("att1@example.com", body)

    def test_other_organizer_gets_404(self):
        self.client.force_login(make_organizer("other"))
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_attendee_is_forbidden(self):
        self.client.force_login(self.attendee)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_anonymous_is_redirected_to_login(self):
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_formula_cells_are_neutralised(self):
        self.attendee.first_name = "=HYPERLINK(1)"
        self.attendee.save()
        self.client.force_login(self.organizer)

        body = self.client.get(self.url).content.decode("utf-8-sig")

        self.assertIn("'=HYPERLINK(1)", body)

    def test_csv_safe_prefixes_dangerous_values_only(self):
        for value in ("=1+1", "+1", "-1", "@cmd"):
            self.assertTrue(csv_safe(value).startswith("'"))
        self.assertEqual(csv_safe("Asha Rao"), "Asha Rao")
        
def local(day, hour=0, minute=0):
    return timezone.make_aware(datetime.combine(day, time(hour, minute)))


class CalendarTests(TestCase):
    def setUp(self):
        self.organizer = make_organizer()
        self.day = timezone.localdate() + timedelta(days=30)

    def get_ics(self, event):
        return self.client.get(reverse("events:event_calendar", args=[event.pk]))

    def test_ics_has_correct_utc_start_and_headers(self):
        event = make_event(self.organizer, title="Launch", start_datetime=local(self.day, 18, 30))

        response = self.get_ics(event)
        body = response.content.decode()

        self.assertIn("text/calendar", response["Content-Type"])
        self.assertIn("BEGIN:VEVENT", body)
        self.assertIn(f"DTSTART:{self.day:%Y%m%d}T130000Z", body)  # 18:30 IST == 13:00 UTC
        self.assertIn(f"DTEND:{self.day:%Y%m%d}T140000Z", body)
        self.assertTrue(body.endswith("\r\n"))

    def test_special_characters_are_escaped(self):
        event = make_event(self.organizer, title="Rock, Pop; Jazz")
        self.assertIn("SUMMARY:Rock\\, Pop\\; Jazz", self.get_ics(event).content.decode())

    def test_long_lines_are_folded_to_75_bytes(self):
        event = make_event(self.organizer, description="é" * 400)
        body = self.get_ics(event).content.decode()
        for line in body.split("\r\n"):
            self.assertLessEqual(len(line.encode("utf-8")), 75)

    def test_cancelled_event_has_no_calendar_file(self):
        event = make_event(self.organizer, status="cancelled")
        self.assertEqual(self.get_ics(event).status_code, 404)