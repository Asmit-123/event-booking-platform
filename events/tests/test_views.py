from datetime import timedelta

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from events.models import Event

from .helpers import event_form_data, make_attendee, make_event, make_organizer, register


class OrganizerViewTestCase(TestCase):
    """Shared setup: a logged-in organizer, a second organizer and an attendee."""

    def setUp(self):
        self.organizer = make_organizer()
        self.other = make_organizer("other")
        self.attendee = make_attendee()
        self.client.force_login(self.organizer)
        self.dashboard_url = reverse("events:organizer_dashboard")


class OrganizerPagesRoleTests(OrganizerViewTestCase):
    def all_urls(self):
        event = make_event(self.organizer)
        return [
            self.dashboard_url,
            reverse("events:event_create"),
            reverse("events:event_edit", args=[event.pk]),
            reverse("events:event_cancel", args=[event.pk]),
            reverse("events:event_attendees", args=[event.pk]),
        ]

    def test_anonymous_users_are_sent_to_login(self):
        urls = self.all_urls()
        self.client.logout()
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertRedirects(response, f"{reverse('accounts:login')}?next={url}")

    def test_attendees_are_forbidden(self):
        urls = self.all_urls()
        self.client.force_login(self.attendee)
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)

    def test_attendee_cannot_cancel_by_posting(self):
        event = make_event(self.organizer)
        self.client.force_login(self.attendee)

        response = self.client.post(reverse("events:event_cancel", args=[event.pk]))

        self.assertEqual(response.status_code, 403)
        event.refresh_from_db()
        self.assertEqual(event.status, Event.Status.ACTIVE)


class EventCreateViewTests(OrganizerViewTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse("events:event_create")

    def test_page_loads(self):
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_valid_post_creates_event_owned_by_the_logged_in_organizer(self):
        response = self.client.post(self.url, event_form_data(title="Launch party"))

        self.assertRedirects(response, self.dashboard_url)
        event = Event.objects.get()
        self.assertEqual(event.title, "Launch party")
        self.assertEqual(event.organizer, self.organizer)

    def test_forged_organizer_and_status_fields_are_ignored(self):
        data = event_form_data(organizer=self.other.pk, status="cancelled")

        self.client.post(self.url, data)

        event = Event.objects.get()
        self.assertEqual(event.organizer, self.organizer)
        self.assertEqual(event.status, Event.Status.ACTIVE)

    def test_past_date_shows_an_error_and_creates_nothing(self):
        past = (timezone.localtime() - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")

        response = self.client.post(self.url, event_form_data(start_datetime=past))

        self.assertEqual(response.status_code, 200)
        self.assertIn("start_datetime", response.context["form"].errors)
        self.assertEqual(Event.objects.count(), 0)

    def test_zero_seat_limit_shows_an_error_and_creates_nothing(self):
        response = self.client.post(self.url, event_form_data(seat_limit=0))

        self.assertIn("seat_limit", response.context["form"].errors)
        self.assertEqual(Event.objects.count(), 0)

    def test_missing_fields_show_errors(self):
        response = self.client.post(self.url, {})

        for field in ("title", "description", "venue", "start_datetime", "seat_limit"):
            self.assertIn(field, response.context["form"].errors)


class OrganizerDashboardTests(OrganizerViewTestCase):
    def test_shows_only_own_events(self):
        make_event(self.organizer, title="My event")
        make_event(self.other, title="Someone else's event")

        response = self.client.get(self.dashboard_url)

        self.assertContains(response, "My event")
        self.assertNotContains(response, "Someone else&#x27;s event")
        self.assertNotContains(response, "Someone else")

    def test_shows_seats_taken_out_of_the_limit(self):
        event = make_event(self.organizer, seat_limit=10)
        register(event, self.attendee)
        register(event, make_attendee("second"))

        response = self.client.get(self.dashboard_url)

        self.assertContains(response, "2 / 10")

    def test_empty_state_is_shown_when_there_are_no_events(self):
        response = self.client.get(self.dashboard_url)

        self.assertContains(response, "You have not created any events yet.")

    def test_cancelled_event_has_no_edit_or_cancel_buttons(self):
        event = make_event(self.organizer, status=Event.Status.CANCELLED)

        response = self.client.get(self.dashboard_url)

        self.assertNotContains(response, reverse("events:event_edit", args=[event.pk]))
        self.assertNotContains(response, reverse("events:event_cancel", args=[event.pk]))
        self.assertContains(response, reverse("events:event_attendees", args=[event.pk]))

    def test_user_supplied_text_is_escaped(self):
        make_event(self.organizer, title="<b>Bold</b>")

        response = self.client.get(self.dashboard_url)

        self.assertContains(response, "&lt;b&gt;Bold&lt;/b&gt;")
        self.assertNotContains(response, "<b>Bold</b>")


class EventEditViewTests(OrganizerViewTestCase):
    def setUp(self):
        super().setUp()
        self.event = make_event(self.organizer)
        self.url = reverse("events:event_edit", args=[self.event.pk])

    def test_form_is_prefilled_with_current_values(self):
        response = self.client.get(self.url)

        self.assertContains(response, 'value="Sample event"')

    def test_valid_post_updates_the_event(self):
        response = self.client.post(self.url, event_form_data(title="Updated title"))

        self.assertRedirects(response, self.dashboard_url)
        self.event.refresh_from_db()
        self.assertEqual(self.event.title, "Updated title")

    def test_other_organizers_event_returns_404_and_is_unchanged(self):
        foreign = make_event(self.other, title="Theirs")
        url = reverse("events:event_edit", args=[foreign.pk])

        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.post(url, event_form_data(title="Hijacked")).status_code, 404)

        foreign.refresh_from_db()
        self.assertEqual(foreign.title, "Theirs")

    def test_nonexistent_event_returns_404(self):
        url = reverse("events:event_edit", args=[999999])
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_seat_limit_below_registered_count_shows_a_field_error(self):
        register(self.event, self.attendee)
        register(self.event, make_attendee("second"))

        response = self.client.post(self.url, event_form_data(seat_limit=1))

        self.assertIn("seat_limit", response.context["form"].errors)
        self.event.refresh_from_db()
        self.assertEqual(self.event.seat_limit, 10)

    def test_forged_status_field_is_ignored(self):
        self.client.post(self.url, event_form_data(status="cancelled"))

        self.event.refresh_from_db()
        self.assertEqual(self.event.status, Event.Status.ACTIVE)

    def test_cancelled_event_redirects_to_the_dashboard(self):
        self.event.status = Event.Status.CANCELLED
        self.event.save()

        response = self.client.get(self.url)

        self.assertRedirects(response, self.dashboard_url)


class EventCancelViewTests(OrganizerViewTestCase):
    def setUp(self):
        super().setUp()
        self.event = make_event(self.organizer)
        self.url = reverse("events:event_cancel", args=[self.event.pk])

    def test_get_shows_confirmation_and_changes_nothing(self):
        register(self.event, self.attendee)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["registered"], 1)
        self.event.refresh_from_db()
        self.assertEqual(self.event.status, Event.Status.ACTIVE)

    def test_post_cancels_the_event_and_keeps_registrations(self):
        register(self.event, self.attendee)

        response = self.client.post(self.url)

        self.assertRedirects(response, self.dashboard_url)
        self.event.refresh_from_db()
        self.assertEqual(self.event.status, Event.Status.CANCELLED)
        self.assertEqual(self.event.registrations.count(), 1)

    def test_other_organizers_event_returns_404_and_is_unchanged(self):
        foreign = make_event(self.other)
        url = reverse("events:event_cancel", args=[foreign.pk])

        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.post(url).status_code, 404)

        foreign.refresh_from_db()
        self.assertEqual(foreign.status, Event.Status.ACTIVE)

    def test_already_cancelled_event_redirects_to_the_dashboard(self):
        self.event.status = Event.Status.CANCELLED
        self.event.save()

        response = self.client.post(self.url)

        self.assertRedirects(response, self.dashboard_url)

    def test_post_without_a_csrf_token_is_rejected(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.organizer)

        response = client.post(self.url)

        self.assertEqual(response.status_code, 403)
        self.event.refresh_from_db()
        self.assertEqual(self.event.status, Event.Status.ACTIVE)


class EventAttendeesViewTests(OrganizerViewTestCase):
    def setUp(self):
        super().setUp()
        self.event = make_event(self.organizer)
        self.url = reverse("events:event_attendees", args=[self.event.pk])

    def test_owner_sees_registered_attendees_with_email(self):
        register(self.event, self.attendee)

        response = self.client.get(self.url)

        self.assertContains(response, self.attendee.email)
        self.assertContains(response, "Test Attendee")

    def test_empty_state_is_shown_when_nobody_registered(self):
        response = self.client.get(self.url)

        self.assertContains(response, "Nobody has registered for this event yet.")

    def test_other_organizers_event_returns_404_and_leaks_nothing(self):
        foreign = make_event(self.other)
        register(foreign, self.attendee)

        response = self.client.get(reverse("events:event_attendees", args=[foreign.pk]))

        self.assertEqual(response.status_code, 404)
        self.assertNotContains(response, self.attendee.email, status_code=404)

    def test_cancelled_event_is_still_viewable_with_its_registrations(self):
        register(self.event, self.attendee)
        self.event.status = Event.Status.CANCELLED
        self.event.save()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cancelled")
        self.assertContains(response, self.attendee.email)