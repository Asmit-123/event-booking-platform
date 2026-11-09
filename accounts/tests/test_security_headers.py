import re

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from events.tests.helpers import make_attendee, make_event, make_organizer

from .helpers import PASSWORD, create_user

INLINE_SCRIPT = re.compile(r"<script(?![^>]*\bsrc=)[^>]*>", re.IGNORECASE)
INLINE_HANDLER = re.compile(
    r"\son(?:click|load|submit|change|input|error|focus|blur|key\w+|mouse\w+)\s*=", re.IGNORECASE
)


class SecurityHeaderTests(TestCase):
    def test_security_headers_are_sent(self):
        response = self.client.get(reverse("events:home"))

        self.assertEqual(response["X-Frame-Options"], "DENY")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response["Referrer-Policy"], "same-origin")
        self.assertEqual(response["Cross-Origin-Opener-Policy"], "same-origin")

    def test_content_security_policy_is_strict(self):
        policy = self.client.get(reverse("events:home"))["Content-Security-Policy"]

        for directive in (
            "default-src 'self'",
            "script-src 'self'",
            "style-src 'self'",
            "object-src 'none'",
            "frame-ancestors 'none'",
            "form-action 'self'",
        ):
            self.assertIn(directive, policy)
        self.assertNotIn("unsafe-inline", policy)
        self.assertNotIn("unsafe-eval", policy)


class CookieFlagTests(TestCase):
    def test_the_session_cookie_is_http_only_and_same_site(self):
        user = create_user()

        self.client.post(reverse("accounts:login"), {"username": user.email, "password": PASSWORD})

        cookie = self.client.cookies["sessionid"]
        self.assertTrue(cookie["httponly"])
        self.assertEqual(cookie["samesite"], "Lax")

    def test_the_csrf_cookie_is_http_only_and_same_site(self):
        self.client.get(reverse("accounts:login"))

        cookie = self.client.cookies["csrftoken"]
        self.assertTrue(cookie["httponly"])
        self.assertEqual(cookie["samesite"], "Lax")


class PagesAreCspCleanTests(TestCase):
    """Inline scripts, inline styles and inline handlers would be blocked by the policy."""

    def test_rendered_pages_contain_no_inline_code(self):
        organizer = make_organizer()
        event = make_event(organizer)
        pages = [
            (None, reverse("events:home")),
            (None, reverse("events:event_list")),
            (None, reverse("events:event_detail", args=[event.pk])),
            (None, reverse("accounts:login")),
            (None, reverse("accounts:signup")),
            (organizer, reverse("events:organizer_dashboard")),
            (organizer, reverse("events:event_create")),
            (organizer, reverse("events:event_edit", args=[event.pk])),
            (organizer, reverse("events:event_cancel", args=[event.pk])),
            (organizer, reverse("events:event_attendees", args=[event.pk])),
            (make_attendee(), reverse("registrations:my_registrations")),
        ]
        for user, url in pages:
            with self.subTest(url=url):
                self.client.logout()
                if user:
                    self.client.force_login(user)
                html = self.client.get(url).content.decode()

                self.assertIsNone(INLINE_SCRIPT.search(html))
                self.assertIsNone(INLINE_HANDLER.search(html))
                self.assertNotIn("<style", html.lower())
                self.assertNotRegex(html, r'\sstyle\s*=')