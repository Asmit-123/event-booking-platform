from datetime import timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from events.forms import EventForm
from events.services import create_event
from events.tests.helpers import event_form_data, make_attendee, make_event, make_organizer
from registrations.services import register_for_event


class OptionalRegistrationDeadlineTests(TestCase):
    def setUp(self):
        self.organizer = make_organizer()
        self.attendee = make_attendee()

    def test_event_can_be_created_without_a_deadline(self):
        event = make_event(self.organizer)
        self.assertIsNone(event.registration_deadline)

    def test_deadline_must_be_before_event_start(self):
        start = timezone.now() + timedelta(days=3)
        with self.assertRaises(ValidationError):
            create_event(
                self.organizer,
                title="Deadline test",
                description="Test description",
                venue="Test venue",
                start_datetime=start,
                seat_limit=10,
                registration_deadline=start,
            )

    def test_registration_is_rejected_after_deadline(self):
        event = make_event(
            self.organizer,
            registration_deadline=timezone.now() - timedelta(minutes=1),
        )
        with self.assertRaises(ValidationError):
            register_for_event(self.attendee, event.pk)

    def test_form_deadline_checkbox_is_optional(self):
        data = event_form_data()
        form = EventForm(data)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertIsNone(form.cleaned_data["registration_deadline"])

    def test_enabled_deadline_is_required_and_must_precede_start(self):
        data = event_form_data()
        data["use_registration_deadline"] = "on"
        form = EventForm(data)
        self.assertFalse(form.is_valid())
        self.assertIn("registration_deadline", form.errors)
