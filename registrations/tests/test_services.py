from datetime import timedelta

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, connection, transaction
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from events import services as event_services
from events.tests.helpers import event_fields, make_attendee, make_event, make_organizer
from registrations import services
from registrations.models import Registration


class RegisterForEventTests(TestCase):
    def setUp(self):
        self.organizer = make_organizer()
        self.attendee = make_attendee("att1")
        self.other = make_attendee("att2")
        self.third = make_attendee("att3")
        self.event = make_event(self.organizer, seat_limit=2)

    def test_attendee_can_register(self):
        registration = services.register_for_event(self.attendee, self.event.pk)

        self.assertEqual(registration.event, self.event)
        self.assertEqual(registration.attendee, self.attendee)
        self.assertEqual(self.event.registrations.count(), 1)

    def test_duplicate_registration_is_refused(self):
        services.register_for_event(self.attendee, self.event.pk)

        with self.assertRaises(ValidationError):
            services.register_for_event(self.attendee, self.event.pk)

        self.assertEqual(self.event.registrations.count(), 1)

    def test_organizer_cannot_register(self):
        with self.assertRaises(PermissionDenied):
            services.register_for_event(self.organizer, self.event.pk)

        self.assertEqual(self.event.registrations.count(), 0)

    def test_cancelled_event_is_refused(self):
        cancelled = make_event(self.organizer, status="cancelled")

        with self.assertRaises(ValidationError):
            services.register_for_event(self.attendee, cancelled.pk)

        self.assertEqual(cancelled.registrations.count(), 0)

    def test_past_event_is_refused(self):
        past = make_event(self.organizer, start_datetime=timezone.now() - timedelta(days=1))

        with self.assertRaises(ValidationError):
            services.register_for_event(self.attendee, past.pk)

        self.assertEqual(past.registrations.count(), 0)

    def test_full_event_is_refused(self):
        services.register_for_event(self.attendee, self.event.pk)
        services.register_for_event(self.other, self.event.pk)

        with self.assertRaises(ValidationError):
            services.register_for_event(self.third, self.event.pk)

        self.assertEqual(self.event.registrations.count(), 2)

    def test_last_seat_can_be_taken(self):
        services.register_for_event(self.attendee, self.event.pk)

        services.register_for_event(self.other, self.event.pk)

        self.assertEqual(self.event.registrations.count(), 2)

    def test_registering_takes_a_row_lock(self):
        with CaptureQueriesContext(connection) as queries:
            services.register_for_event(self.attendee, self.event.pk)

        self.assertTrue(any("FOR UPDATE" in q["sql"] for q in queries.captured_queries))

    def test_database_constraint_backs_up_the_service(self):
        services.register_for_event(self.attendee, self.event.pk)

        with self.assertRaises(IntegrityError), transaction.atomic():
            Registration.objects.create(event=self.event, attendee=self.attendee)

    def test_one_attendee_can_register_for_different_events(self):
        other_event = make_event(self.organizer, seat_limit=1)

        services.register_for_event(self.attendee, self.event.pk)
        services.register_for_event(self.attendee, other_event.pk)

        self.assertEqual(self.attendee.registrations.count(), 2)

    def test_lowering_the_limit_to_the_registered_count_closes_registration(self):
        event = make_event(self.organizer, seat_limit=3)
        services.register_for_event(self.attendee, event.pk)
        services.register_for_event(self.other, event.pk)

        event_services.update_event(self.organizer, event.pk, **event_fields(seat_limit=2))

        with self.assertRaises(ValidationError):
            services.register_for_event(self.third, event.pk)

    def test_cancelling_the_event_closes_registration(self):
        event_services.cancel_event(self.organizer, self.event.pk)

        with self.assertRaises(ValidationError):
            services.register_for_event(self.attendee, self.event.pk)