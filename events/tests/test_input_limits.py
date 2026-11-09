from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from events import services
from events.forms import EventForm
from events.models import DESCRIPTION_MAX_LENGTH, Event

from .helpers import event_fields, event_form_data, make_organizer


class DescriptionLimitTests(TestCase):
    def test_form_rejects_a_description_over_the_limit(self):
        form = EventForm(event_form_data(description="x" * (DESCRIPTION_MAX_LENGTH + 1)))

        self.assertIn("description", form.errors)

    def test_form_accepts_a_description_at_the_limit(self):
        form = EventForm(event_form_data(description="x" * DESCRIPTION_MAX_LENGTH))

        self.assertNotIn("description", form.errors)

    def test_service_rejects_it_too(self):
        organizer = make_organizer()

        with self.assertRaises(ValidationError):
            services.create_event(
                organizer, **event_fields(description="x" * (DESCRIPTION_MAX_LENGTH + 1))
            )

        self.assertEqual(Event.objects.count(), 0)


class RequestSizeLimitTests(TestCase):
    def test_an_oversized_request_body_is_rejected_and_nothing_is_created(self):
        self.client.force_login(make_organizer())

        response = self.client.post(
            reverse("events:event_create"), event_form_data(title="x" * 300_000)
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Event.objects.count(), 0)