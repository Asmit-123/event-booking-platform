from datetime import timedelta
from unittest.mock import patch

from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts import throttle
from accounts.models import LoginAttempt, User

from .helpers import PASSWORD, create_user


class LoginThrottleTests(TestCase):
    def setUp(self):
        self.url = reverse("accounts:login")
        self.user = create_user(email="aarav@example.com", username="aarav")

    def attempt(self, email="aarav@example.com", password=PASSWORD, ip="10.0.0.1", client=None):
        client = client or self.client
        return client.post(self.url, {"username": email, "password": password}, REMOTE_ADDR=ip)

    def fail(self, times, **kwargs):
        for _ in range(times):
            self.attempt(password="Wrong-Pass-123", **kwargs)

    def test_five_failures_lock_the_client_even_for_the_correct_password(self):
        self.fail(5)

        response = self.attempt()

        self.assertEqual(response.status_code, 429)
        self.assertContains(response, "Too many failed attempts", status_code=429)
        self.assertIn("Retry-After", response)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_four_failures_do_not_lock(self):
        self.fail(4)

        response = self.attempt()

        self.assertEqual(response.status_code, 302)
        self.assertIn("_auth_user_id", self.client.session)

    def test_unknown_emails_are_throttled_the_same_way(self):
        self.fail(5, email="nobody@example.com")

        response = self.attempt(email="nobody@example.com")

        self.assertEqual(response.status_code, 429)
        self.assertContains(response, "Too many failed attempts", status_code=429)

    def test_another_email_from_the_same_address_is_not_locked_by_the_pair_limit(self):
        other = create_user(User.Role.ORGANIZER)
        self.fail(5)

        response = self.attempt(email=other.email)

        self.assertEqual(response.status_code, 302)

    def test_another_address_is_not_locked(self):
        self.fail(5, ip="10.0.0.1")

        response = self.attempt(ip="10.0.0.2")

        self.assertEqual(response.status_code, 302)

    def test_many_failures_from_one_address_lock_every_email(self):
        LoginAttempt.objects.bulk_create(
            [LoginAttempt(ip_address="10.0.0.1", email=f"x{n}@example.com") for n in range(20)]
        )

        response = self.attempt()

        self.assertEqual(response.status_code, 429)

    def test_the_lock_expires_after_the_window(self):
        self.fail(5)
        later = timezone.now() + throttle.WINDOW + timedelta(minutes=1)

        with patch("django.utils.timezone.now", return_value=later):
            response = self.attempt()

        self.assertEqual(response.status_code, 302)

    def test_a_successful_login_clears_earlier_failures(self):
        self.fail(4)
        self.attempt()
        self.client.logout()
        self.fail(4)

        response = self.attempt()

        self.assertEqual(response.status_code, 302)

    def test_requests_rejected_for_csrf_are_not_counted(self):
        client = Client(enforce_csrf_checks=True)

        for _ in range(6):
            response = self.attempt(client=client)
            self.assertEqual(response.status_code, 403)

        self.assertEqual(LoginAttempt.objects.count(), 0)

    def test_get_requests_are_not_counted(self):
        for _ in range(10):
            self.client.get(self.url, REMOTE_ADDR="10.0.0.1")

        self.assertEqual(LoginAttempt.objects.count(), 0)

    def test_old_attempts_are_deleted_when_a_new_failure_is_recorded(self):
        old = LoginAttempt.objects.create(ip_address="10.0.0.5", email="old@example.com")
        LoginAttempt.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(hours=1))

        self.fail(1)

        self.assertFalse(LoginAttempt.objects.filter(pk=old.pk).exists())

    def test_the_admin_login_is_throttled_too(self):
        url = reverse("admin:login")
        data = {"username": "root@example.com", "password": "Wrong-Pass-123", "next": "/admin/"}

        for _ in range(5):
            self.assertEqual(self.client.post(url, data, REMOTE_ADDR="10.0.0.1").status_code, 200)

        self.assertEqual(self.client.post(url, data, REMOTE_ADDR="10.0.0.1").status_code, 429)


class ClientIpTests(TestCase):
    def request(self, forwarded=None, remote="10.0.0.9"):
        extra = {"REMOTE_ADDR": remote}
        if forwarded:
            extra["HTTP_X_FORWARDED_FOR"] = forwarded
        return RequestFactory().get("/", **extra)

    def test_the_remote_address_is_used_by_default(self):
        self.assertEqual(throttle.client_ip(self.request("1.1.1.1")), "10.0.0.9")

    @override_settings(TRUSTED_PROXY_COUNT=1)
    def test_one_trusted_proxy_means_the_rightmost_entry_and_ignores_forged_ones(self):
        self.assertEqual(throttle.client_ip(self.request("6.6.6.6, 1.2.3.4")), "1.2.3.4")

    @override_settings(TRUSTED_PROXY_COUNT=2)
    def test_two_trusted_proxies_mean_the_second_entry_from_the_right(self):
        self.assertEqual(throttle.client_ip(self.request("6.6.6.6, 1.2.3.4, 10.1.1.1")), "1.2.3.4")

    @override_settings(TRUSTED_PROXY_COUNT=1)
    def test_missing_or_invalid_headers_fall_back_to_the_remote_address(self):
        self.assertEqual(throttle.client_ip(self.request()), "10.0.0.9")
        self.assertEqual(throttle.client_ip(self.request("not-an-ip")), "10.0.0.9")

    @override_settings(TRUSTED_PROXY_COUNT=3)
    def test_fewer_entries_than_trusted_proxies_falls_back_to_the_remote_address(self):
        self.assertEqual(throttle.client_ip(self.request("1.2.3.4")), "10.0.0.9")