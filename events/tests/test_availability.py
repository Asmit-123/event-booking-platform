from django.test import TestCase
from django.urls import reverse

from events import selectors

from .helpers import make_attendee, make_event, make_organizer, register


class AvailabilityFilterTests(TestCase):
    def setUp(self):
        organizer = make_organizer()
        make_event(organizer, title="Open Event", seat_limit=5)
        full = make_event(organizer, title="Full Event", seat_limit=1)
        register(full, make_attendee("att1"))

    def test_selector_hides_full_events(self):
        rows = selectors.only_with_seats(selectors.upcoming_events())
        self.assertEqual([e.title for e in rows], ["Open Event"])

    def test_view_hides_full_events_only_when_checked(self):
        url = reverse("events:event_list")

        everything = self.client.get(url)
        filtered = self.client.get(url, {"available_only": "on"})

        self.assertContains(everything, "Full Event")
        self.assertContains(filtered, "Open Event")
        self.assertNotContains(filtered, "Full Event")