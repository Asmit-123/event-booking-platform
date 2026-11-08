import threading

from django.core.exceptions import ValidationError
from django.db import connection
from django.test import TransactionTestCase

from events import services as event_services
from events.tests.helpers import event_fields, make_attendee, make_event, make_organizer, register
from registrations import services


class ConcurrentBookingTests(TransactionTestCase):
    """Real threads and real commits: TestCase would hide races inside one transaction."""

    def setUp(self):
        self.organizer = make_organizer()

    def run_concurrently(self, actions):
        """Start every action at the same instant and report how each one ended."""
        outcomes = []
        barrier = threading.Barrier(len(actions))

        def attempt(action):
            try:
                connection.ensure_connection()
                barrier.wait(timeout=30)
                action()
                outcomes.append("done")
            except ValidationError:
                outcomes.append("refused")
            except Exception as error:
                outcomes.append(f"error: {error!r}")
            finally:
                connection.close()

        threads = [threading.Thread(target=attempt, args=(action,)) for action in actions]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=60)
        return outcomes

    def registering(self, event, attendees):
        return [lambda a=attendee: services.register_for_event(a, event.pk) for attendee in attendees]

    def test_only_one_of_many_competing_registrations_gets_the_last_seat(self):
        event = make_event(self.organizer, seat_limit=1)
        attendees = [make_attendee(f"att{i}") for i in range(8)]

        outcomes = self.run_concurrently(self.registering(event, attendees))

        self.assertEqual(outcomes.count("done"), 1, outcomes)
        self.assertEqual(outcomes.count("refused"), 7, outcomes)
        self.assertEqual(event.registrations.count(), 1)

    def test_registrations_never_exceed_the_limit_with_several_seats(self):
        event = make_event(self.organizer, seat_limit=3)
        attendees = [make_attendee(f"att{i}") for i in range(8)]

        outcomes = self.run_concurrently(self.registering(event, attendees))

        self.assertEqual(outcomes.count("done"), 3, outcomes)
        self.assertEqual(event.registrations.count(), 3)

    def test_one_attendee_submitting_repeatedly_registers_once(self):
        event = make_event(self.organizer, seat_limit=5)
        attendee = make_attendee()

        outcomes = self.run_concurrently(self.registering(event, [attendee] * 4))

        self.assertEqual(outcomes.count("done"), 1, outcomes)
        self.assertEqual(outcomes.count("refused"), 3, outcomes)
        self.assertEqual(event.registrations.count(), 1)

    def test_editing_the_limit_and_registering_never_leave_more_people_than_seats(self):
        event = make_event(self.organizer, seat_limit=10)
        for number in range(4):
            register(event, make_attendee(f"early{number}"))
        newcomers = [make_attendee(f"late{number}") for number in range(4)]

        actions = self.registering(event, newcomers)
        actions.append(
            lambda: event_services.update_event(self.organizer, event.pk, **event_fields(seat_limit=4))
        )
        outcomes = self.run_concurrently(actions)

        self.assertEqual([o for o in outcomes if o.startswith("error")], [], outcomes)
        event.refresh_from_db()
        self.assertLessEqual(event.registrations.count(), event.seat_limit)