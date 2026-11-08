from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from events import selectors

from .helpers import make_attendee, make_event, make_organizer, register


class OrganizerEventsSelectorTests(TestCase):
    def setUp(self):
        self.organizer = make_organizer()
        self.other = make_organizer("other")

    def test_returns_only_own_events_newest_first(self):
        now = timezone.now()
        make_event(self.organizer, title="Soon", start_datetime=now + timedelta(days=1))
        make_event(self.organizer, title="Later", start_datetime=now + timedelta(days=5))
        make_event(self.other, title="Not mine")

        titles = [event.title for event in selectors.organizer_events(self.organizer)]

        self.assertEqual(titles, ["Later", "Soon"])

    def test_counts_seats_taken_in_a_single_query(self):
        busy = make_event(self.organizer, title="Busy")
        make_event(self.organizer, title="Empty")
        register(busy, make_attendee("att1"))
        register(busy, make_attendee("att2"))

        with self.assertNumQueries(1):
            counts = {e.title: e.seats_taken for e in selectors.organizer_events(self.organizer)}

        self.assertEqual(counts, {"Busy": 2, "Empty": 0})


class EventRegistrationsSelectorTests(TestCase):
    def test_returns_registrations_in_order_with_attendees_in_one_query(self):
        organizer = make_organizer()
        event = make_event(organizer)
        first = make_attendee("att1")
        second = make_attendee("att2")
        register(event, first)
        register(event, second)

        with self.assertNumQueries(1):
            emails = [r.attendee.email for r in selectors.event_registrations(event)]

        self.assertEqual(emails, [first.email, second.email])