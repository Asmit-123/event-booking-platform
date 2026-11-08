from django.contrib import admin
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.admin import CustomUserAdmin
from accounts.models import User
from accounts.tests.helpers import PASSWORD
from events.models import Event

from .helpers import make_event, make_organizer


class AdminCannotBypassRulesTests(TestCase):
    def setUp(self):
        self.organizer = make_organizer()
        self.event = make_event(self.organizer, seat_limit=10)
        self.superuser = User.objects.create_superuser(
            username="root",
            email="root@example.com",
            password=PASSWORD,
            first_name="Root",
            last_name="User",
        )
        self.client.force_login(self.superuser)

    def test_events_cannot_be_added_through_the_admin(self):
        response = self.client.get(reverse("admin:events_event_add"))

        self.assertEqual(response.status_code, 403)

    def test_protected_event_fields_ignore_posted_values(self):
        url = reverse("admin:events_event_change", args=[self.event.pk])
        data = {
            "title": "Renamed in admin",
            "description": "d",
            "venue": "v",
            "seat_limit": 1,
            "status": "cancelled",
            "start_datetime_0": "2000-01-01",
            "start_datetime_1": "00:00:00",
        }

        self.client.post(url, data)

        self.event.refresh_from_db()
        self.assertEqual(self.event.title, "Renamed in admin")
        self.assertEqual(self.event.seat_limit, 10)
        self.assertEqual(self.event.status, Event.Status.ACTIVE)
        self.assertGreater(self.event.start_datetime, timezone.now())

    def test_a_users_role_is_read_only_once_the_user_exists(self):
        user_admin = CustomUserAdmin(User, admin.site)

        self.assertIn("role", user_admin.get_readonly_fields(None, self.organizer))
        self.assertNotIn("role", user_admin.get_readonly_fields(None, None))