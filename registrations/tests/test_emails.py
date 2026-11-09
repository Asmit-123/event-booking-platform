from unittest import mock

from django.core import mail
from django.test import TestCase
from django.urls import reverse

from events.tests.helpers import make_attendee, make_event, make_organizer, register
from registrations.models import Registration


class ConfirmationEmailTests(TestCase):
    def setUp(self):
        self.organizer = make_organizer()
        self.attendee = make_attendee("att1")
        self.client.force_login(self.attendee)

    def post_register(self, event):
        return self.client.post(reverse("registrations:register", args=[event.pk]))

    def test_successful_registration_sends_one_email(self):
        event = make_event(self.organizer, title="Jazz Night")

        self.post_register(event)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["att1@example.com"])
        self.assertIn("Jazz Night", mail.outbox[0].subject)

    def test_duplicate_registration_sends_no_second_email(self):
        event = make_event(self.organizer)
        self.post_register(event)
        self.post_register(event)

        self.assertEqual(len(mail.outbox), 1)

    def test_full_event_sends_no_email(self):
        event = make_event(self.organizer, seat_limit=1)
        register(event, make_attendee("other"))

        self.post_register(event)

        self.assertEqual(len(mail.outbox), 0)

    def test_mail_failure_does_not_undo_the_registration(self):
        event = make_event(self.organizer)

        with mock.patch("registrations.emails.send_mail", side_effect=OSError("smtp down")):
            with self.assertLogs("registrations.emails", level="ERROR"):
                response = self.post_register(event)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Registration.objects.filter(event=event, attendee=self.attendee).exists())

    def test_newline_in_title_cannot_break_the_subject_header(self):
        event = make_event(self.organizer, title="Line1\nBcc: evil@example.com")

        self.post_register(event)

        self.assertEqual(len(mail.outbox), 1)
        self.assertNotIn("\n", mail.outbox[0].subject)