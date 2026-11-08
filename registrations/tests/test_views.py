from datetime import timedelta

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from events.models import Event
from events.tests.helpers import make_attendee, make_event, make_organizer, register
from registrations.models import Registration


def flash_messages(response):
    return [str(message) for message in response.context["messages"]]


class RegisterViewTests(TestCase):
    def setUp(self):
        self.organizer = make_organizer()
        self.attendee = make_attendee("att1")
        self.other = make_attendee("att2")
        self.event = make_event(self.organizer, seat_limit=1)
        self.url = reverse("registrations:register", args=[self.event.pk])
        self.detail_url = reverse("events:event_detail", args=[self.event.pk])
        self.client.force_login(self.attendee)

    def test_attendee_can_register_and_returns_to_the_event_page(self):
        response = self.client.post(self.url)

        self.assertRedirects(response, self.detail_url)
        registration = Registration.objects.get()
        self.assertEqual(registration.event, self.event)
        self.assertEqual(registration.attendee, self.attendee)

    def test_success_shows_a_message(self):
        response = self.client.post(self.url, follow=True)

        self.assertIn("You are registered", flash_messages(response)[0])

    def test_registering_twice_shows_an_error_and_keeps_one_registration(self):
        self.client.post(self.url, follow=True)

        response = self.client.post(self.url, follow=True)

        self.assertIn("already registered", flash_messages(response)[0])
        self.assertEqual(Registration.objects.count(), 1)

    def test_full_event_shows_an_error_and_adds_nothing(self):
        register(self.event, self.other)

        response = self.client.post(self.url, follow=True)

        self.assertIn("fully booked", flash_messages(response)[0])
        self.assertEqual(Registration.objects.count(), 1)

    def test_cancelled_event_is_refused(self):
        self.event.status = Event.Status.CANCELLED
        self.event.save()

        response = self.client.post(self.url, follow=True)

        self.assertIn("cancelled", flash_messages(response)[0])
        self.assertEqual(Registration.objects.count(), 0)

    def test_started_event_is_refused(self):
        self.event.start_datetime = timezone.now() - timedelta(hours=1)
        self.event.save()

        response = self.client.post(self.url, follow=True)

        self.assertIn("already started", flash_messages(response)[0])
        self.assertEqual(Registration.objects.count(), 0)

    def test_organizer_is_forbidden_and_nothing_is_created(self):
        self.client.force_login(self.organizer)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(Registration.objects.count(), 0)

    def test_anonymous_user_is_sent_to_login_and_nothing_is_created(self):
        self.client.logout()

        response = self.client.post(self.url)

        self.assertRedirects(response, f"{reverse('accounts:login')}?next={self.url}")
        self.assertEqual(Registration.objects.count(), 0)

    def test_get_is_not_allowed_and_creates_nothing(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 405)
        self.assertEqual(Registration.objects.count(), 0)

    def test_post_without_a_csrf_token_is_rejected(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.attendee)

        response = client.post(self.url)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(Registration.objects.count(), 0)

    def test_forged_attendee_field_is_ignored(self):
        self.client.post(self.url, {"attendee": self.other.pk})

        registration = Registration.objects.get()
        self.assertEqual(registration.attendee, self.attendee)

    def test_unknown_event_returns_404(self):
        response = self.client.post(reverse("registrations:register", args=[999999]))

        self.assertEqual(response.status_code, 404)


class MyRegistrationsViewTests(TestCase):
    def setUp(self):
        self.organizer = make_organizer()
        self.attendee = make_attendee("att1")
        self.other = make_attendee("att2")
        self.url = reverse("registrations:my_registrations")
        self.client.force_login(self.attendee)

    def test_empty_state(self):
        response = self.client.get(self.url)

        self.assertContains(response, "You have not registered for any events yet.")

    def test_shows_only_the_attendees_own_registrations(self):
        register(make_event(self.organizer, title="Mine"), self.attendee)
        register(make_event(self.organizer, title="Theirs"), self.other)

        response = self.client.get(self.url)

        self.assertContains(response, "Mine")
        self.assertNotContains(response, "Theirs")

    def test_cancelled_events_are_kept_in_the_earlier_section(self):
        cancelled = make_event(self.organizer, title="Called off", status=Event.Status.CANCELLED)
        register(cancelled, self.attendee)

        response = self.client.get(self.url)

        self.assertEqual(response.context["upcoming"], [])
        self.assertEqual([r.event.title for r in response.context["earlier"]], ["Called off"])
        self.assertContains(response, "Cancelled and past")

    def test_titles_are_escaped(self):
        register(make_event(self.organizer, title="<b>Bold</b>"), self.attendee)

        response = self.client.get(self.url)

        self.assertContains(response, "&lt;b&gt;Bold&lt;/b&gt;")
        self.assertNotContains(response, "<b>Bold</b>")

    def test_organizers_are_forbidden(self):
        self.client.force_login(self.organizer)

        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_anonymous_users_are_sent_to_login(self):
        self.client.logout()

        response = self.client.get(self.url)

        self.assertRedirects(response, f"{reverse('accounts:login')}?next={self.url}")