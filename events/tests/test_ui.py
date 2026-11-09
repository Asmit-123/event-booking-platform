from datetime import timedelta

from django.template.loader import render_to_string
from django.templatetags.static import static
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from events.models import Event

from .helpers import event_form_data, make_attendee, make_event, make_organizer, register


class LandingPageTests(TestCase):
    def setUp(self):
        self.url = reverse("events:home")
        self.organizer = make_organizer()

    def test_page_is_public_and_has_a_headline(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Find an event. Save your seat.")

    def test_anonymous_visitors_are_invited_to_sign_up(self):
        response = self.client.get(self.url)

        self.assertContains(response, reverse("accounts:signup"))

    def test_attendees_see_their_registrations_and_no_organizer_links(self):
        self.client.force_login(make_attendee())

        response = self.client.get(self.url)

        self.assertContains(response, reverse("registrations:my_registrations"))
        self.assertNotContains(response, reverse("events:organizer_dashboard"))

    def test_organizers_are_offered_event_creation(self):
        self.client.force_login(self.organizer)

        response = self.client.get(self.url)

        self.assertContains(response, "Create an event")
        self.assertContains(response, reverse("events:event_create"))

    def test_shows_at_most_three_upcoming_events_soonest_first(self):
        now = timezone.now()
        for days, title in enumerate(["Soonest", "Second", "Third", "Fourth"], start=1):
            make_event(self.organizer, title=title, start_datetime=now + timedelta(days=days))

        response = self.client.get(self.url)

        titles = [event.title for event in response.context["featured"]]
        self.assertEqual(titles, ["Soonest", "Second", "Third"])
        self.assertNotContains(response, "Fourth")

    def test_cancelled_and_past_events_are_not_featured(self):
        make_event(self.organizer, title="Called off", status=Event.Status.CANCELLED)
        make_event(self.organizer, title="Finished", start_datetime=timezone.now() - timedelta(days=1))

        response = self.client.get(self.url)

        self.assertNotContains(response, "Called off")
        self.assertNotContains(response, "Finished")

    def test_empty_state_when_there_are_no_events(self):
        response = self.client.get(self.url)

        self.assertContains(response, "no upcoming events")


class ErrorPageTests(TestCase):
    def test_unknown_url_shows_the_friendly_404_page(self):
        response = self.client.get("/no-such-page/")

        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, "404.html")

    def test_csrf_failure_shows_the_friendly_page(self):
        client = Client(enforce_csrf_checks=True)

        response = client.post(reverse("accounts:login"), {})

        self.assertEqual(response.status_code, 403)
        self.assertTemplateUsed(response, "403_csrf.html")

    def test_wrong_role_shows_the_friendly_403_page(self):
        self.client.force_login(make_attendee())

        response = self.client.get(reverse("events:organizer_dashboard"))

        self.assertEqual(response.status_code, 403)
        self.assertTemplateUsed(response, "403.html")

    def test_500_page_is_standalone(self):
        html = render_to_string("500.html")

        self.assertIn("Something went wrong", html)
        self.assertNotIn("{%", html)


class LayoutAndAccessibilityTests(TestCase):
    def test_skip_link_main_landmark_and_language(self):
        response = self.client.get(reverse("events:event_list"))

        self.assertContains(response, 'href="#main"')
        self.assertContains(response, 'id="main"')
        self.assertContains(response, '<html lang="en">')

    def test_shared_assets_are_linked(self):
        response = self.client.get(reverse("events:home"))

        self.assertContains(response, static("css/app.css"))
        self.assertContains(response, static("js/app.js"))

    def test_current_page_is_marked_in_the_navigation(self):
        browse = self.client.get(reverse("events:event_list"))
        home = self.client.get(reverse("events:home"))

        self.assertContains(browse, 'aria-current="page"', count=1)
        self.assertNotContains(home, 'aria-current="page"')

    def test_organizer_dashboard_link_is_marked_current(self):
        self.client.force_login(make_organizer())

        response = self.client.get(reverse("events:organizer_dashboard"))

        self.assertContains(response, 'aria-current="page"', count=1)

    def test_navigation_follows_the_role(self):
        anonymous = self.client.get(reverse("events:home"))
        self.assertContains(anonymous, reverse("accounts:login"))
        self.assertNotContains(anonymous, reverse("events:organizer_dashboard"))

        self.client.force_login(make_organizer())
        organizer = self.client.get(reverse("events:home"))
        self.assertContains(organizer, reverse("events:organizer_dashboard"))
        self.assertNotContains(organizer, reverse("registrations:my_registrations"))

    def test_messages_are_dismissible_and_errors_use_the_danger_style(self):
        event = make_event(make_organizer())
        url = reverse("registrations:register", args=[event.pk])
        self.client.force_login(make_attendee())
        self.client.post(url)

        response = self.client.post(url, follow=True)

        self.assertContains(response, "alert-danger")
        self.assertContains(response, 'data-bs-dismiss="alert"')


class FormStylingTests(TestCase):
    def test_invalid_event_form_marks_the_fields(self):
        self.client.force_login(make_organizer())

        response = self.client.post(reverse("events:event_create"), {})

        self.assertContains(response, "is-invalid")
        self.assertContains(response, 'aria-invalid="true"')

    def test_errors_added_after_validation_also_mark_the_field(self):
        organizer = make_organizer()
        event = make_event(organizer)
        register(event, make_attendee("att1"))
        register(event, make_attendee("att2"))
        self.client.force_login(organizer)

        response = self.client.post(
            reverse("events:event_edit", args=[event.pk]), event_form_data(seat_limit=1)
        )

        self.assertContains(response, "cannot be lower than")
        self.assertContains(response, "is-invalid")

    def test_signup_uses_accessible_radio_markup(self):
        response = self.client.get(reverse("accounts:signup"))

        self.assertContains(response, "<fieldset>")
        self.assertContains(response, "form-check-input")

    def test_state_changing_forms_prevent_double_submits(self):
        organizer = make_organizer()
        event = make_event(organizer)
        self.client.force_login(organizer)
        for url in (
            reverse("events:event_create"),
            reverse("events:event_cancel", args=[event.pk]),
        ):
            with self.subTest(url=url):
                self.assertContains(self.client.get(url), "data-prevent-double-submit")

        self.client.force_login(make_attendee())
        detail = self.client.get(reverse("events:event_detail", args=[event.pk]))
        self.assertContains(detail, "data-prevent-double-submit")

        self.client.logout()
        for name in ("accounts:login", "accounts:signup"):
            with self.subTest(page=name):
                self.assertContains(self.client.get(reverse(name)), "data-prevent-double-submit")