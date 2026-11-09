from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from events import selectors
from events.models import Event

from .helpers import make_attendee, make_event, make_organizer, register


class OrganizerStatsTests(TestCase):
    def setUp(self):
        self.organizer = make_organizer()

    def test_summary_numbers(self):
        a = make_event(self.organizer, seat_limit=4)
        b = make_event(self.organizer, seat_limit=6)
        make_event(self.organizer, seat_limit=5, status=Event.Status.CANCELLED)
        make_event(self.organizer, seat_limit=10, start_datetime=timezone.now() - timedelta(days=1))
        register(a, make_attendee("a1"))
        register(a, make_attendee("a2"))
        register(b, make_attendee("a3"))

        stats = selectors.summarize_organizer_events(list(selectors.organizer_events(self.organizer)))

        self.assertEqual(stats["total_events"], 4)
        self.assertEqual(stats["upcoming_events"], 2)
        self.assertEqual(stats["cancelled_events"], 1)
        self.assertEqual(stats["total_registrations"], 3)
        self.assertEqual(stats["fill_rate"], 15)  # 3 taken of 20 seats in non-cancelled events

    def test_no_events_gives_zero_fill_rate_not_a_crash(self):
        self.assertEqual(selectors.summarize_organizer_events([])["fill_rate"], 0)

    def test_dashboard_only_counts_own_events(self):
        make_event(self.organizer)
        other = make_organizer("other")
        register(make_event(other), make_attendee("a1"))
        self.client.force_login(self.organizer)

        response = self.client.get(reverse("events:organizer_dashboard"))

        self.assertEqual(response.context["stats"]["total_events"], 1)
        self.assertEqual(response.context["stats"]["total_registrations"], 0)