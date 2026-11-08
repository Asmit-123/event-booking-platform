from django.test import TestCase
from django.urls import reverse

from accounts.models import User

from .helpers import PASSWORD, create_user


class LoginTests(TestCase):
    def setUp(self):
        self.url = reverse("accounts:login")
        self.home = reverse("events:home")
        self.user = create_user(email="aarav@example.com", username="aarav")

    def login(self, email="aarav@example.com", password=PASSWORD, **extra):
        return self.client.post(
            self.url, {"username": email, "password": password, **extra}
        )

    def test_login_with_correct_credentials(self):
        response = self.login()

        self.assertRedirects(response, self.home)
        self.assertIn("_auth_user_id", self.client.session)

    def test_email_is_matched_ignoring_case(self):
        response = self.login(email="AARAV@Example.com")

        self.assertRedirects(response, self.home)
        self.assertIn("_auth_user_id", self.client.session)

    def test_wrong_password_and_unknown_email_give_the_same_message(self):
        wrong_password = self.login(password="Wrong-Pass-123")
        unknown_email = self.login(email="nobody@example.com")

        expected = ["Incorrect email or password."]
        self.assertEqual(list(wrong_password.context["form"].non_field_errors()), expected)
        self.assertEqual(list(unknown_email.context["form"].non_field_errors()), expected)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_inactive_user_cannot_log_in(self):
        self.user.is_active = False
        self.user.save()

        response = self.login()

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_local_next_url_is_followed(self):
        organizer = create_user(User.Role.ORGANIZER)

        response = self.login(email=organizer.email, next=reverse("events:organizer_dashboard"))

        self.assertRedirects(response, reverse("events:organizer_dashboard"))

    def test_external_next_url_is_ignored(self):
        response = self.login(next="https://example.org/phishing")

        self.assertRedirects(response, self.home)

    def test_logged_in_user_is_redirected_from_login_page(self):
        self.client.force_login(self.user)

        response = self.client.get(self.url)

        self.assertRedirects(response, self.home)


class LogoutTests(TestCase):
    def setUp(self):
        self.url = reverse("accounts:logout")
        self.client.force_login(create_user())

    def test_get_logout_is_not_allowed(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 405)
        self.assertIn("_auth_user_id", self.client.session)

    def test_post_logout_ends_the_session(self):
        response = self.client.post(self.url)

        self.assertRedirects(response, reverse("events:home"))
        self.assertNotIn("_auth_user_id", self.client.session)