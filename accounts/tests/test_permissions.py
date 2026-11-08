from django.test import TestCase
from django.urls import reverse

from accounts.models import User

from .helpers import create_user


class RoleAccessTests(TestCase):
    def setUp(self):
        self.organizer_url = reverse("events:organizer_dashboard")
        self.attendee_url = reverse("registrations:my_registrations")
        self.organizer = create_user(User.Role.ORGANIZER)
        self.attendee = create_user(User.Role.ATTENDEE)

    def test_anonymous_users_are_sent_to_login_with_next(self):
        login_url = reverse("accounts:login")
        for url in (self.organizer_url, self.attendee_url):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertRedirects(response, f"{login_url}?next={url}")

    def test_organizer_can_open_organizer_page(self):
        self.client.force_login(self.organizer)
        self.assertEqual(self.client.get(self.organizer_url).status_code, 200)

    def test_attendee_can_open_attendee_page(self):
        self.client.force_login(self.attendee)
        self.assertEqual(self.client.get(self.attendee_url).status_code, 200)

    def test_attendee_is_forbidden_from_organizer_page(self):
        self.client.force_login(self.attendee)

        response = self.client.get(self.organizer_url)

        self.assertEqual(response.status_code, 403)
        self.assertTemplateUsed(response, "403.html")

    def test_organizer_is_forbidden_from_attendee_page(self):
        self.client.force_login(self.organizer)

        response = self.client.get(self.attendee_url)

        self.assertEqual(response.status_code, 403)

    def test_role_claimed_in_the_request_is_not_trusted(self):
        self.client.force_login(self.attendee)

        get_response = self.client.get(self.organizer_url, {"role": "organizer"})
        post_response = self.client.post(self.organizer_url, {"role": "organizer"})

        self.assertEqual(get_response.status_code, 403)
        self.assertEqual(post_response.status_code, 403)

    def test_navigation_shows_only_the_links_for_the_role(self):
        self.client.force_login(self.attendee)
        page = self.client.get(self.attendee_url)
        self.assertContains(page, self.attendee_url)
        self.assertNotContains(page, self.organizer_url)