from django.test import TestCase
from django.urls import reverse

from accounts.models import User

from .helpers import PASSWORD, create_user


class SignUpTests(TestCase):
    def setUp(self):
        self.url = reverse("accounts:signup")

    def valid_data(self, **overrides):
        data = {
            "email": "aarav@example.com",
            "username": "aarav",
            "first_name": "Aarav",
            "last_name": "Test",
            "role": "attendee",
            "password1": PASSWORD,
            "password2": PASSWORD,
        }
        data.update(overrides)
        return data

    def test_page_loads(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_valid_signup_creates_user_and_logs_in(self):
        response = self.client.post(self.url, self.valid_data(role="organizer"))

        self.assertRedirects(response, reverse("events:home"))
        user = User.objects.get(email="aarav@example.com")
        self.assertEqual(user.role, User.Role.ORGANIZER)
        self.assertNotEqual(user.password, PASSWORD)
        self.assertTrue(user.check_password(PASSWORD))
        self.assertIn("_auth_user_id", self.client.session)

    def test_role_is_required(self):
        response = self.client.post(self.url, self.valid_data(role=""))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.count(), 0)
        self.assertIn("role", response.context["form"].errors)

    def test_invalid_role_is_rejected(self):
        response = self.client.post(self.url, self.valid_data(role="admin"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.count(), 0)
        self.assertIn("role", response.context["form"].errors)

    def test_privilege_flags_in_post_data_are_ignored(self):
        data = self.valid_data(is_staff="on", is_superuser="on")
        self.client.post(self.url, data)

        user = User.objects.get(email="aarav@example.com")
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_duplicate_email_is_rejected_ignoring_case(self):
        create_user(email="aarav@example.com", username="existing")

        response = self.client.post(self.url, self.valid_data(email="AARAV@example.com"))

        self.assertEqual(User.objects.count(), 1)
        self.assertIn("email", response.context["form"].errors)

    def test_weak_password_is_rejected(self):
        data = self.valid_data(password1="12345678", password2="12345678")
        response = self.client.post(self.url, data)

        self.assertEqual(User.objects.count(), 0)
        self.assertIn("password2", response.context["form"].errors)

    def test_logged_in_user_is_redirected_away(self):
        self.client.force_login(create_user())

        response = self.client.get(self.url)

        self.assertRedirects(response, reverse("events:home"))