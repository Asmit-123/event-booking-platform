from datetime import timedelta

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from events import services
from events.models import Event

from .helpers import event_fields, make_attendee, make_event, make_organizer, register


def issued_row_lock(queries):
    return any("FOR UPDATE" in query["sql"] for query in queries.captured_queries)


class CreateEventServiceTests(TestCase):
    def setUp(self):
        self.organizer = make_organizer()
        self.attendee = make_attendee()

    def test_organizer_can_create_event(self):
        event = services.create_event(self.organizer, **event_fields())

        self.assertEqual(event.organizer, self.organizer)
        self.assertEqual(event.status, Event.Status.ACTIVE)
        self.assertEqual(Event.objects.count(), 1)

    def test_attendee_cannot_create_event(self):
        with self.assertRaises(PermissionDenied):
            services.create_event(self.attendee, **event_fields())
        self.assertEqual(Event.objects.count(), 0)

    def test_start_in_the_past_is_rejected(self):
        past = timezone.now() - timedelta(minutes=1)
        with self.assertRaises(ValidationError):
            services.create_event(self.organizer, **event_fields(start_datetime=past))
        self.assertEqual(Event.objects.count(), 0)

    def test_zero_seat_limit_is_rejected(self):
        with self.assertRaises(ValidationError):
            services.create_event(self.organizer, **event_fields(seat_limit=0))
        self.assertEqual(Event.objects.count(), 0)


class UpdateEventServiceTests(TestCase):
    def setUp(self):
        self.organizer = make_organizer()
        self.other = make_organizer("other")
        self.event = make_event(self.organizer)
        self.attendees = [make_attendee("att1"), make_attendee("att2")]

    def update(self, **overrides):
        return services.update_event(self.organizer, self.event.pk, **event_fields(**overrides))

    def register_all(self):
        for attendee in self.attendees:
            register(self.event, attendee)

    def test_owner_can_update_event(self):
        self.update(title="Renamed", seat_limit=20)

        self.event.refresh_from_db()
        self.assertEqual(self.event.title, "Renamed")
        self.assertEqual(self.event.seat_limit, 20)

    def test_seat_limit_cannot_drop_below_registered_count(self):
        self.register_all()

        with self.assertRaises(ValidationError) as caught:
            self.update(seat_limit=1)

        self.assertIn("seat_limit", caught.exception.message_dict)
        self.event.refresh_from_db()
        self.assertEqual(self.event.seat_limit, 10)

    def test_seat_limit_equal_to_registered_count_is_allowed(self):
        self.register_all()

        self.update(seat_limit=2)

        self.event.refresh_from_db()
        self.assertEqual(self.event.seat_limit, 2)

    def test_other_organizer_cannot_update(self):
        with self.assertRaises(PermissionDenied):
            services.update_event(self.other, self.event.pk, **event_fields(title="Hijacked"))

        self.event.refresh_from_db()
        self.assertEqual(self.event.title, "Sample event")

    def test_new_start_in_the_past_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.update(start_datetime=timezone.now() - timedelta(days=1))

    def test_cancelled_event_cannot_be_edited(self):
        self.event.status = Event.Status.CANCELLED
        self.event.save()

        with self.assertRaises(ValidationError):
            self.update(title="Too late")

    def test_past_event_cannot_be_edited(self):
        past = make_event(self.organizer, start_datetime=timezone.now() - timedelta(days=1))

        with self.assertRaises(ValidationError):
            services.update_event(self.organizer, past.pk, **event_fields())

    def test_update_takes_a_row_lock(self):
        with CaptureQueriesContext(connection) as queries:
            self.update(title="Locked")

        self.assertTrue(issued_row_lock(queries))


class CancelEventServiceTests(TestCase):
    def setUp(self):
        self.organizer = make_organizer()
        self.other = make_organizer("other")
        self.attendee = make_attendee()
        self.event = make_event(self.organizer)

    def test_owner_can_cancel_and_registrations_are_kept(self):
        register(self.event, self.attendee)

        cancelled = services.cancel_event(self.organizer, self.event.pk)

        self.assertEqual(cancelled.status, Event.Status.CANCELLED)
        self.assertEqual(self.event.registrations.count(), 1)

    def test_other_organizer_cannot_cancel(self):
        with self.assertRaises(PermissionDenied):
            services.cancel_event(self.other, self.event.pk)

        self.event.refresh_from_db()
        self.assertEqual(self.event.status, Event.Status.ACTIVE)

    def test_cancelling_twice_is_rejected(self):
        services.cancel_event(self.organizer, self.event.pk)

        with self.assertRaises(ValidationError):
            services.cancel_event(self.organizer, self.event.pk)

    def test_past_event_cannot_be_cancelled(self):
        past = make_event(self.organizer, start_datetime=timezone.now() - timedelta(days=1))

        with self.assertRaises(ValidationError):
            services.cancel_event(self.organizer, past.pk)

    def test_updated_at_is_refreshed(self):
        before = self.event.updated_at

        services.cancel_event(self.organizer, self.event.pk)

        self.event.refresh_from_db()
        self.assertGreater(self.event.updated_at, before)

    def test_cancel_takes_a_row_lock(self):
        with CaptureQueriesContext(connection) as queries:
            services.cancel_event(self.organizer, self.event.pk)

        self.assertTrue(issued_row_lock(queries))