from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from events.models import Event
from events.tests.helpers import make_attendee, make_event, make_organizer, register
from registrations import selectors


class AttendeeRegistrationsSelectorTests(TestCase):
    def setUp(self):
        self.organizer = make_organizer()
        self.attendee = make_attendee("att1")
        self.other = make_attendee("att2")
        now = timezone.now()
        self.later = make_event(self.organizer, title="Later", start_datetime=now + timedelta(days=2))
        self.soon = make_event(self.organizer, title="Soon", start_datetime=now + timedelta(days=1))
        self.cancelled = make_event(
            self.organizer, title="Cancelled", start_datetime=now + timedelta(days=3), status=Event.Status.CANCELLED
        )
        self.past = make_event(self.organizer, title="Past", start_datetime=now - timedelta(days=2))

    def register_all(self, attendee):
        for event in (self.later, self.soon, self.cancelled, self.past):
            register(event, attendee)

    def test_registrations_are_split_and_ordered(self):
        self.register_all(self.attendee)

        upcoming, earlier = selectors.attendee_registrations(self.attendee)

        self.assertEqual([r.event.title for r in upcoming], ["Soon", "Later"])
        self.assertEqual([r.event.title for r in earlier], ["Cancelled", "Past"])

    def test_only_the_attendees_own_registrations_are_returned(self):
        register(self.soon, self.attendee)
        register(self.later, self.other)

        upcoming, earlier = selectors.attendee_registrations(self.attendee)

        self.assertEqual([r.event.title for r in upcoming], ["Soon"])
        self.assertEqual(earlier, [])

    def test_everything_comes_in_one_query(self):
        self.register_all(self.attendee)

        with self.assertNumQueries(1):
            upcoming, earlier = selectors.attendee_registrations(self.attendee)
            [(r.event.title, r.event.organizer.first_name) for r in upcoming + earlier]