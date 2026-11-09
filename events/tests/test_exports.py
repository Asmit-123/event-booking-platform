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