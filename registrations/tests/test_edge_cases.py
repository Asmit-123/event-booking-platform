from datetime import timedelta
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase

from events.tests.helpers import make_attendee, make_event, make_organizer
from registrations import services


class RegistrationBoundaryTests(TestCase):
    def setUp(self):
        self.organizer = make_organizer()

    def test_registration_closes_at_the_exact_moment_the_event_starts(self):
        event = make_event(self.organizer)
        early = make_attendee("early")
        late = make_attendee("late")
        one_second_before = event.start_datetime - timedelta(seconds=1)

        with patch("django.utils.timezone.now", return_value=one_second_before):
            services.register_for_event(early, event.pk)

        with patch("django.utils.timezone.now", return_value=event.start_datetime):
            with self.assertRaises(ValidationError):
                services.register_for_event(late, event.pk)

        self.assertEqual(event.registrations.count(), 1)

    def test_filling_every_seat_one_by_one_then_one_more_is_refused(self):
        event = make_event(self.organizer, seat_limit=5)
        for number in range(5):
            services.register_for_event(make_attendee(f"att{number}"), event.pk)

        with self.assertRaises(ValidationError):
            services.register_for_event(make_attendee("extra"), event.pk)

        self.assertEqual(event.registrations.count(), 5)

    def test_a_single_seat_event_can_be_booked_exactly_once(self):
        event = make_event(self.organizer, seat_limit=1)
        services.register_for_event(make_attendee("first"), event.pk)

        with self.assertRaises(ValidationError):
            services.register_for_event(make_attendee("second"), event.pk)

        self.assertEqual(event.registrations.count(), 1)