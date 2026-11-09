from datetime import datetime, time, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from events import selectors
from events.views import EVENTS_PER_PAGE

from .helpers import make_event, make_organizer


def local(day, hour=0, minute=0):
    """A timezone-aware datetime on `day` at hour:minute in the project's time zone."""
    return timezone.make_aware(datetime.combine(day, time(hour, minute)))


class DateRangeSelectorTests(TestCase):
    def setUp(self):
        organizer = make_organizer()
        self.day = timezone.localdate() + timedelta(days=30)
        make_event(organizer, title="Before", start_datetime=local(self.day - timedelta(days=1), 23, 59))
        make_event(organizer, title="Morning", start_datetime=local(self.day, 0, 0))
        make_event(organizer, title="Night", start_datetime=local(self.day, 23, 59))
        make_event(organizer, title="After", start_datetime=local(self.day + timedelta(days=1), 0, 0))

    def titles(self, **kwargs):
        rows = selectors.filter_by_date_range(selectors.upcoming_events(), **kwargs)
        return [event.title for event in rows]

    def test_no_dates_returns_everything(self):
        self.assertEqual(self.titles(), ["Before", "Morning", "Night", "After"])

    def test_date_from_includes_midnight_boundary(self):
        self.assertEqual(self.titles(date_from=self.day), ["Morning", "Night", "After"])

    def test_date_to_includes_the_whole_end_day(self):
        self.assertEqual(self.titles(date_to=self.day), ["Before", "Morning", "Night"])

    def test_same_day_range_returns_only_that_day(self):
        self.assertEqual(self.titles(date_from=self.day, date_to=self.day), ["Morning", "Night"])

    def test_range_with_no_events_is_empty(self):
        far = self.day + timedelta(days=100)
        self.assertEqual(self.titles(date_from=far, date_to=far), [])


class DateFilterViewTests(TestCase):
    def setUp(self):
        self.organizer = make_organizer()
        self.url = reverse("events:event_list")
        self.day = timezone.localdate() + timedelta(days=30)

    def test_view_filters_by_date_range(self):
        make_event(self.organizer, title="On the day", start_datetime=local(self.day, 10))
        make_event(self.organizer, title="Next week", start_datetime=local(self.day + timedelta(days=7), 10))

        response = self.client.get(self.url, {"date_from": self.day.isoformat(), "date_to": self.day.isoformat()})

        self.assertContains(response, "On the day")
        self.assertNotContains(response, "Next week")

    def test_end_before_start_is_rejected_and_list_stays_unfiltered(self):
        make_event(self.organizer, title="On the day", start_datetime=local(self.day, 10))

        response = self.client.get(
            self.url,
            {"date_from": self.day.isoformat(), "date_to": (self.day - timedelta(days=1)).isoformat()},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("date_to", response.context["form"].errors)
        self.assertContains(response, "On the day")

    def test_garbage_and_out_of_range_dates_do_not_crash(self):
        for bad in ("not-a-date", "0001-01-01", "9999-12-31"):
            for field in ("date_from", "date_to"):
                with self.subTest(field=field, value=bad):
                    response = self.client.get(self.url, {field: bad})
                    self.assertEqual(response.status_code, 200)
                    self.assertIn(field, response.context["form"].errors)

    def test_dates_combine_with_keyword_search(self):
        make_event(self.organizer, title="Jazz Night", start_datetime=local(self.day, 10))
        make_event(self.organizer, title="Python Meetup", start_datetime=local(self.day, 11))

        response = self.client.get(self.url, {"q": "jazz", "date_from": self.day.isoformat()})

        self.assertContains(response, "Jazz Night")
        self.assertNotContains(response, "Python Meetup")

    def test_pagination_links_keep_the_dates(self):
        for i in range(EVENTS_PER_PAGE + 1):
            make_event(self.organizer, title=f"Event {i}", start_datetime=local(self.day, 10))

        response = self.client.get(self.url, {"date_from": self.day.isoformat()})

        self.assertContains(response, "date_from=")
        self.assertContains(response, "page=2")