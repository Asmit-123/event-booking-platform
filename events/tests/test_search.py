from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from events import selectors
from events.models import Event
from events.views import EVENTS_PER_PAGE

from .helpers import make_event, make_organizer


class SearchSelectorTests(TestCase):
    def setUp(self):
        self.organizer = make_organizer()
        make_event(self.organizer, title="Jazz Night", venue="Blue Hall")
        make_event(self.organizer, title="Python Meetup", venue="Tech Park",
                   description="Talks about Django and testing.")

    def titles(self, term):
        return [e.title for e in selectors.search_events(selectors.upcoming_events(), term)]

    def test_matches_title_case_insensitively(self):
        self.assertEqual(self.titles("jazz"), ["Jazz Night"])

    def test_matches_venue(self):
        self.assertEqual(self.titles("tech park"), ["Python Meetup"])

    def test_matches_description(self):
        self.assertEqual(self.titles("django"), ["Python Meetup"])

    def test_blank_or_whitespace_term_returns_everything(self):
        self.assertEqual(len(self.titles("")), 2)
        self.assertEqual(len(self.titles("   ")), 2)
        self.assertEqual(len(self.titles(None)), 2)

    def test_percent_sign_is_treated_literally(self):
        self.assertEqual(self.titles("%"), [])

    def test_search_never_surfaces_cancelled_or_past_events(self):
        make_event(self.organizer, title="Jazz Cancelled", status=Event.Status.CANCELLED)
        make_event(self.organizer, title="Jazz Past",
                   start_datetime=timezone.now() - timedelta(days=1))
        self.assertEqual(self.titles("jazz"), ["Jazz Night"])


class SearchViewTests(TestCase):
    def setUp(self):
        self.organizer = make_organizer()
        self.url = reverse("events:event_list")

    def test_search_filters_results(self):
        make_event(self.organizer, title="Jazz Night")
        make_event(self.organizer, title="Python Meetup")

        response = self.client.get(self.url, {"q": "jazz"})

        self.assertContains(response, "Jazz Night")
        self.assertNotContains(response, "Python Meetup")

    def test_no_match_shows_search_empty_state(self):
        make_event(self.organizer, title="Jazz Night")

        response = self.client.get(self.url, {"q": "zzz"})

        self.assertContains(response, "No upcoming events match")

    def test_overlong_query_is_rejected_and_list_stays_unfiltered(self):
        make_event(self.organizer, title="Jazz Night")

        response = self.client.get(self.url, {"q": "x" * 101})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Jazz Night")
        self.assertTrue(response.context["form"].errors)

    def test_search_term_is_html_escaped(self):
        response = self.client.get(self.url, {"q": "<script>alert(1)</script>"})

        self.assertNotContains(response, "<script>alert(1)</script>")

    def test_pagination_links_keep_the_search_term(self):
        for i in range(EVENTS_PER_PAGE + 1):
            make_event(self.organizer, title=f"Jazz {i}")

        response = self.client.get(self.url, {"q": "jazz"})

        self.assertContains(response, "q=jazz")
        self.assertContains(response, "page=2")
        
class ThemeToggleTests(TestCase):
    def test_base_template_loads_theme_script_and_toggle(self):
        response = self.client.get(reverse("events:home"))
        self.assertContains(response, "js/theme.js")
        self.assertContains(response, 'id="theme-toggle"')