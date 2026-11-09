from datetime import timedelta, timezone as dt_timezone
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from events import services
from events.forms import EventForm
from events.models import Event
from events.validators import validate_start_in_future

from .helpers import event_fields, event_form_data, make_organizer


class DateBoundaryTests(TestCase):
    def test_start_exactly_now_is_rejected_and_one_second_later_is_accepted(self):
        now = timezone.now()

        with patch("django.utils.timezone.now", return_value=now):
            with self.assertRaises(ValidationError):
                validate_start_in_future(now)
            validate_start_in_future(now + timedelta(seconds=1))


class EventFormEdgeCaseTests(TestCase):
    def test_blank_and_whitespace_only_text_is_rejected(self):
        form = EventForm(event_form_data(title="   ", venue="\t", description="  "))

        self.assertFalse(form.is_valid())
        for field in ("title", "venue", "description"):
            self.assertIn(field, form.errors)

    def test_overlong_title_is_rejected(self):
        form = EventForm(event_form_data(title="x" * 201))

        self.assertIn("title", form.errors)

    def test_seat_limit_boundaries(self):
        cases = {"0": False, "1": True, "2147483647": True, "2147483648": False, "-1": False, "abc": False, "2.5": False, "": False}
        for value, should_be_valid in cases.items():
            with self.subTest(seat_limit=value):
                form = EventForm(event_form_data(seat_limit=value))
                self.assertEqual(form.is_valid(), should_be_valid, form.errors)

    def test_unparseable_date_is_rejected(self):
        form = EventForm(event_form_data(start_datetime="not a date"))

        self.assertIn("start_datetime", form.errors)


class ServiceInputLimitTests(TestCase):
    def test_a_seat_limit_beyond_the_database_range_is_rejected_cleanly(self):
        organizer = make_organizer()

        with self.assertRaises(ValidationError):
            services.create_event(organizer, **event_fields(seat_limit=2**31))

        self.assertEqual(Event.objects.count(), 0)

    def test_unicode_titles_round_trip(self):
        title = "Caf\u00e9 \U0001F389 \u65e5\u672c"
        organizer = make_organizer()
        services.create_event(organizer, **event_fields(title=title))
        self.client.force_login(organizer)

        response = self.client.get(reverse("events:organizer_dashboard"))

        self.assertContains(response, title)


class TimeZoneTests(TestCase):
    def test_form_time_is_read_as_kolkata_time_and_stored_as_utc(self):
        organizer = make_organizer()
        self.client.force_login(organizer)
        year = timezone.now().year + 1

        self.client.post(
            reverse("events:event_create"),
            event_form_data(start_datetime=f"{year}-06-15T18:00"),
        )

        stored = Event.objects.get().start_datetime.astimezone(dt_timezone.utc)
        self.assertEqual((stored.hour, stored.minute), (12, 30))