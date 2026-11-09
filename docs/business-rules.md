# Business rules

Every rule is enforced in the backend, never only by hiding buttons. A rule that can be expressed in the database is. Rules that depend on other rows or on the current time are enforced in the service layer, under a row lock on the event.

## Rule matrix

| # | Rule | Database | Service layer | Views and permissions |
|---|------|----------|---------------|------------------------|
| 1 | Seat limit | `CHECK (seat_limit > 0)` | `register_for_event` locks the event row, counts registrations, refuses when `count >= seat_limit` | Register is POST-only and attendee-only |
| 2 | One seat per person | `UNIQUE (event, attendee)` | Friendly duplicate check under the same lock | Same as rule 1 |
| 3 | Ownership | `PROTECT` foreign keys | `update_event` and `cancel_event` re-check the owner; `create_event` and `register_for_event` re-check the role | Organizer-only and attendee-only decorators; owner-filtered queries return 404 |
| 4 | Valid dates | None (depends on the current time) | `validate_start_in_future`; cancelled and past events are refused for edit, cancel and register | The form gives early feedback |
| 5 | Seat limit changes | None (spans two tables) | `update_event` counts registrations under the lock and refuses a lower limit | The form shows the error on the field |
| 6 | Enforced by the app | Constraints and `PROTECT` | Every rule lives in a service, not in a view | Admin fields that carry rules are read-only |

## Concurrency

`register_for_event`, `update_event` and `cancel_event` all start by locking the same event row (`select_for_update`) inside a transaction. Concurrent requests for one event therefore run one at a time, and each one counts registrations only after the previous one has committed. Different events never block each other.

## Evidence (automated tests)

| Rule | Key tests |
|------|-----------|
| 1 | `RegisterForEventTests.test_full_event_is_refused`, `test_last_seat_can_be_taken`, `ConcurrentBookingTests.test_only_one_of_many_competing_registrations_gets_the_last_seat` |
| 2 | `RegisterForEventTests.test_duplicate_registration_is_refused`, `test_database_constraint_backs_up_the_service`, `ConcurrentBookingTests.test_one_attendee_submitting_repeatedly_registers_once` |
| 3 | `UpdateEventServiceTests.test_other_organizer_cannot_update`, `CancelEventServiceTests.test_other_organizer_cannot_cancel`, `EventEditViewTests.test_other_organizers_event_returns_404_and_is_unchanged`, `EventAttendeesViewTests.test_other_organizers_event_returns_404_and_leaks_nothing` |
| 4 | `CreateEventServiceTests.test_start_in_the_past_is_rejected`, `RegisterForEventTests.test_past_event_is_refused`, `RegistrationBoundaryTests.test_registration_closes_at_the_exact_moment_the_event_starts` |
| 5 | `UpdateEventServiceTests.test_seat_limit_cannot_drop_below_registered_count`, `test_seat_limit_equal_to_registered_count_is_allowed`, `ConcurrentBookingTests.test_editing_the_limit_and_registering_never_leave_more_people_than_seats` |
| 6 | `RegisterViewTests.test_get_is_not_allowed_and_creates_nothing`, `test_post_without_a_csrf_token_is_rejected`, `EventCreateViewTests.test_forged_organizer_and_status_fields_are_ignored`, `AdminCannotBypassRulesTests.test_protected_event_fields_ignore_posted_values` |

## Known limitations

- Registrations for one event are processed one at a time. This is simple and correct at this scale; a very large sale would need a conditional counter update or a queue.
- Attendees cannot cancel their own registrations (not required by the specification).