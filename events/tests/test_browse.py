from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from events import selectors
from events.models import Event
from events.views import EVENTS_PER_PAGE

from .helpers import make_attendee, make_event, make_organizer, register


class UpcomingEventsSelectorTests(TestCase):
    def setUp(self):
        self.organizer = make_organizer()

    def test_includes_only_active_future_events_soonest_first(self):
        now = timezone.now()
        make_event(self.organizer, title="Later", start_datetime=now + timedelta(days=5))
        make_event(self.organizer, title="Soon", start_datetime=now + timedelta(days=1))
        make_event(self.organizer, title="Cancelled", status=Event.Status.CANCELLED)
        make_event(self.organizer, title="Past", start_datetime=now - timedelta(days=1))

        titles = [event.title for event in selectors.upcoming_events()]

        self.assertEqual(titles, ["Soon", "Later"])

    def test_events_with_the_same_start_are_ordered_by_pk(self):
        start = timezone.now() + timedelta(days=3)
        first = make_event(self.organizer, title="First", start_datetime=start)
        second = make_event(self.organizer, title="Second", start_datetime=start)

        pks = [event.pk for event in selectors.upcoming_events()]

        self.assertEqual(pks, [first.pk, second.pk])

    def test_seats_taken_and_left_and_organizer_come_in_one_query(self):
        now = timezone.now()
        full = make_event(self.organizer, title="Full", seat_limit=2, start_datetime=now + timedelta(days=1))
        make_event(self.organizer, title="Empty", seat_limit=5, start_datetime=now + timedelta(days=2))
        register(full, make_attendee("att1"))
        register(full, make_attendee("att2"))

        with self.assertNumQueries(1):
            rows = {
                event.title: (event.seats_taken, event.seats_left, event.organizer.first_name)
                for event in selectors.upcoming_events()
            }

        self.assertEqual(rows["Full"][:2], (2, 0))
        self.assertEqual(rows["Empty"][:2], (0, 5))


class EventListViewTests(TestCase):
    def setUp(self):
        self.organizer = make_organizer()
        self.url = reverse("events:event_list")

    def test_page_is_public(self):
        make_event(self.organizer, title="Open day")

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Open day")

    def test_cancelled_and_past_events_are_hidden(self):
        make_event(self.organizer, title="Hidden cancelled", status=Event.Status.CANCELLED)
        make_event(self.organizer, title="Hidden past", start_datetime=timezone.now() - timedelta(days=1))
        make_event(self.organizer, title="Visible")

        response = self.client.get(self.url)

        self.assertContains(response, "Visible")
        self.assertNotContains(response, "Hidden cancelled")
        self.assertNotContains(response, "Hidden past")

    def test_organizer_name_is_shown_but_never_the_email(self):
        make_event(self.organizer)

        response = self.client.get(self.url)

        self.assertContains(response, "Test Organizer")
        self.assertNotContains(response, self.organizer.email)

    def test_availability_badges(self):
        make_event(self.organizer, title="Roomy", seat_limit=5)
        sold_out = make_event(self.organizer, title="Packed", seat_limit=1)
        register(sold_out, make_attendee())

        response = self.client.get(self.url)

        self.assertContains(response, "5 seats left")
        self.assertContains(response, "Sold out")

    def test_pagination_splits_the_list(self):
        now = timezone.now()
        for number in range(EVENTS_PER_PAGE + 2):
            make_event(self.organizer, title=f"Event {number}", start_datetime=now + timedelta(days=number + 1))

        first = self.client.get(self.url)
        second = self.client.get(self.url, {"page": 2})

        self.assertEqual(len(first.context["page"]), EVENTS_PER_PAGE)
        self.assertEqual(len(second.context["page"]), 2)

    def test_invalid_page_numbers_do_not_crash(self):
        make_event(self.organizer)

        for value in ("abc", "999", "-1", "0"):
            with self.subTest(page=value):
                self.assertEqual(self.client.get(self.url, {"page": value}).status_code, 200)

    def test_empty_state(self):
        response = self.client.get(self.url)

        self.assertContains(response, "no upcoming events")

    def test_titles_are_escaped(self):
        make_event(self.organizer, title="<b>Bold</b>")

        response = self.client.get(self.url)

        self.assertContains(response, "&lt;b&gt;Bold&lt;/b&gt;")
        self.assertNotContains(response, "<b>Bold</b>")


class EventDetailViewTests(TestCase):
    def setUp(self):
        self.organizer = make_organizer()

    def url(self, event):
        return reverse("events:event_detail", args=[event.pk])

    def test_page_is_public_and_shows_the_details(self):
        event = make_event(self.organizer, title="Open day", venue="Main hall", seat_limit=10)
        register(event, make_attendee())

        response = self.client.get(self.url(event))

        self.assertContains(response, "Open day")
        self.assertContains(response, "Main hall")
        self.assertContains(response, "1 of 10 taken")
        self.assertContains(response, "9 left")

    def test_cancelled_event_is_shown_with_a_cancelled_badge(self):
        event = make_event(self.organizer, status=Event.Status.CANCELLED)

        response = self.client.get(self.url(event))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cancelled")

    def test_past_event_is_shown_with_an_ended_badge(self):
        event = make_event(self.organizer, start_datetime=timezone.now() - timedelta(days=1))

        response = self.client.get(self.url(event))

        self.assertContains(response, "Ended")

    def test_unknown_event_returns_404(self):
        response = self.client.get(reverse("events:event_detail", args=[999999]))

        self.assertEqual(response.status_code, 404)

    def test_attendee_emails_are_never_exposed(self):
        event = make_event(self.organizer)
        attendee = make_attendee()
        register(event, attendee)

        response = self.client.get(self.url(event))

        self.assertNotContains(response, attendee.email)

    def test_description_is_escaped_but_keeps_paragraphs(self):
        event = make_event(
            self.organizer,
            description="<script>alert(1)</script>\n\nSecond paragraph",
        )

        response = self.client.get(self.url(event))

        self.assertNotContains(response, "<script>alert(1)</script>")
        self.assertContains(response, "&lt;script&gt;")
        self.assertContains(response, "<p>Second paragraph</p>")


class EventDetailRegistrationAreaTests(TestCase):
    """What the registration area shows each kind of visitor (a convenience layer only)."""

    def setUp(self):
        self.organizer = make_organizer()
        self.attendee = make_attendee()
        self.event = make_event(self.organizer, seat_limit=2)
        self.url = reverse("events:event_detail", args=[self.event.pk])
        self.register_url = reverse("registrations:register", args=[self.event.pk])

    def test_anonymous_visitor_is_invited_to_log_in_and_returns_here(self):
        response = self.client.get(self.url)

        self.assertContains(response, f"?next={self.url}")
        self.assertNotContains(response, self.register_url)

    def test_attendee_sees_the_register_button(self):
        self.client.force_login(self.attendee)

        response = self.client.get(self.url)

        self.assertContains(response, self.register_url)

    def test_registered_attendee_sees_confirmation_instead_of_the_button(self):
        register(self.event, self.attendee)
        self.client.force_login(self.attendee)

        response = self.client.get(self.url)

        self.assertContains(response, "You are registered for this event.")
        self.assertNotContains(response, self.register_url)

    def test_no_button_when_the_event_is_full(self):
        register(self.event, make_attendee("att2"))
        register(self.event, make_attendee("att3"))
        self.client.force_login(self.attendee)

        response = self.client.get(self.url)

        self.assertContains(response, "fully booked")
        self.assertNotContains(response, self.register_url)

    def test_no_button_when_the_event_is_cancelled(self):
        self.event.status = Event.Status.CANCELLED
        self.event.save()
        self.client.force_login(self.attendee)

        response = self.client.get(self.url)

        self.assertContains(response, "has been cancelled")
        self.assertNotContains(response, self.register_url)

    def test_no_button_when_the_event_has_started(self):
        self.event.start_datetime = timezone.now() - timedelta(hours=1)
        self.event.save()
        self.client.force_login(self.attendee)

        response = self.client.get(self.url)

        self.assertContains(response, "already started")
        self.assertNotContains(response, self.register_url)

    def test_organizer_sees_a_notice_and_no_button(self):
        self.client.force_login(self.organizer)

        response = self.client.get(self.url)

        self.assertContains(response, "Organizer accounts cannot register")
        self.assertNotContains(response, self.register_url)