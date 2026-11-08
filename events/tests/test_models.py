from datetime import timedelta

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from events.models import Event

from .helpers import make_event, make_organizer


class EventModelTests(TestCase):
    def setUp(self):
        self.organizer = make_organizer()

    def test_upcoming_active_event_is_editable(self):
        event = make_event(self.organizer)
        self.assertFalse(event.is_cancelled)
        self.assertFalse(event.is_past)
        self.assertTrue(event.is_editable)

    def test_cancelled_event_is_not_editable(self):
        event = make_event(self.organizer, status=Event.Status.CANCELLED)
        self.assertTrue(event.is_cancelled)
        self.assertFalse(event.is_editable)

    def test_past_event_is_not_editable(self):
        event = make_event(self.organizer, start_datetime=timezone.now() - timedelta(days=1))
        self.assertTrue(event.is_past)
        self.assertFalse(event.is_editable)

    def test_database_rejects_zero_seat_limit(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_event(self.organizer, seat_limit=0)