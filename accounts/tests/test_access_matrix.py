from django.test import TestCase
from django.urls import URLPattern, URLResolver, get_resolver, reverse

from accounts.models import User

from .helpers import create_user

OUR_NAMESPACES = {"accounts", "events", "registrations"}

# route name: (reverse arguments, status an anonymous GET must produce)
ANONYMOUS_GET = {
    "accounts:signup": ([], 200),
    "accounts:login": ([], 200),
    "accounts:logout": ([], 405),
    "events:home": ([], 200),
    "events:event_list": ([], 200),
    "events:event_detail": ([1], 404),
    "events:organizer_dashboard": ([], 302),
    "events:event_create": ([], 302),
    "events:event_edit": ([1], 302),
    "events:event_cancel": ([1], 302),
    "events:event_attendees": ([1], 302),
    "registrations:my_registrations": ([], 302),
    "registrations:register": ([1], 302),
}
ORGANIZER_ONLY = {
    "events:organizer_dashboard",
    "events:event_create",
    "events:event_edit",
    "events:event_cancel",
    "events:event_attendees",
}
ATTENDEE_ONLY = {"registrations:my_registrations", "registrations:register"}


def named_urls(patterns=None, namespace=""):
    patterns = get_resolver().url_patterns if patterns is None else patterns
    for pattern in patterns:
        if isinstance(pattern, URLResolver):
            inner = f"{namespace}{pattern.namespace}:" if pattern.namespace else namespace
            yield from named_urls(pattern.url_patterns, inner)
        elif isinstance(pattern, URLPattern) and pattern.name:
            yield f"{namespace}{pattern.name}"


class AccessMatrixTests(TestCase):
    def test_every_route_is_classified(self):
        ours = {name for name in named_urls() if name.split(":")[0] in OUR_NAMESPACES}

        self.assertEqual(ours, set(ANONYMOUS_GET))

    def test_anonymous_visitors_get_the_expected_response(self):
        login_url = reverse("accounts:login")
        for name, (args, status) in ANONYMOUS_GET.items():
            with self.subTest(route=name):
                response = self.client.get(reverse(name, args=args))

                self.assertEqual(response.status_code, status)
                if status == 302:
                    self.assertTrue(response["Location"].startswith(login_url))

    def test_every_redirected_route_is_role_restricted(self):
        redirected = {name for name, (_, status) in ANONYMOUS_GET.items() if status == 302}

        self.assertEqual(redirected, ORGANIZER_ONLY | ATTENDEE_ONLY)

    def test_role_restricted_routes_refuse_the_other_role(self):
        cases = ((User.Role.ATTENDEE, ORGANIZER_ONLY), (User.Role.ORGANIZER, ATTENDEE_ONLY))
        for role, forbidden in cases:
            self.client.force_login(create_user(role))
            for name in forbidden:
                with self.subTest(role=role, route=name):
                    args = ANONYMOUS_GET[name][0]

                    self.assertEqual(self.client.get(reverse(name, args=args)).status_code, 403)
            self.client.logout()