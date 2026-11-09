# Database Schema

This document describes the application's domain tables based on the Django models.

## Entity relationship overview

```text
accounts_user (1) -------- (many) events_event
       |                         organizer
       |
       +------------------- (many) registrations_registration
                                 attendee

events_event (1) -------- (many) registrations_registration
                              event
```

Each registration links one attendee to one event. The pair `(event_id, attendee_id)` is unique.

## Tables

### accounts_user

Custom Django user table (Django's configured table name is derived from the app/model).

| Field | Type / meaning | Notes |
|---|---|---|
| id | Big integer primary key | Django default auto field |
| email | Email | Unique; used as `USERNAME_FIELD`; normalized to lowercase on model save |
| username | String | Inherited from Django's AbstractUser |
| first_name, last_name | String | Required profile fields |
| role | Choice string | `organizer` or `attendee`; defaults to attendee |
| password and auth fields | Django auth fields | Passwords are stored as Django password hashes, not plaintext |

### accounts_loginattempt

Tracks failed login attempts for throttling.

| Field | Type / meaning | Notes |
|---|---|---|
| id | Primary key | Django default |
| ip_address | Generic IP address | Client address used by throttle logic |
| email | String, max 254 | Submitted email, blank allowed |
| created_at | Timestamp | Automatically set on creation |

Indexes support lookup by `(ip_address, created_at)` and `(ip_address, email, created_at)`. Old attempts older than the throttle window are deleted when a new failed attempt is recorded.

### events_event

An event published by an organizer.

| Field | Type / meaning | Notes |
|---|---|---|
| id | Big integer primary key | Django default |
| organizer_id | Foreign key to user | `PROTECT`; related name `organized_events` |
| title | String, max 200 | Required |
| description | Text | Maximum 5,000 characters |
| venue | String, max 255 | Required |
| start_datetime | Date/time | Stored as timezone-aware datetime |
| seat_limit | Positive integer | Must be greater than zero |
| status | Choice string | `active` or `cancelled`; defaults to active |
| created_at, updated_at | Timestamps | Automatic creation/update timestamps |

Constraints and indexes:
- Check constraint: `seat_limit > 0`.
- Index: `(status, start_datetime)`.
- Organizer foreign key uses `PROTECT`, preserving event ownership history from accidental user deletion.

### registrations_registration

A single attendee's registration for an event.

| Field | Type / meaning | Notes |
|---|---|---|
| id | Big integer primary key | Django default |
| event_id | Foreign key to event | `PROTECT`; related name `registrations` |
| attendee_id | Foreign key to user | `PROTECT`; related name `registrations` |
| created_at | Timestamp | Automatically set on creation |

Constraint:
- Unique constraint on `(event_id, attendee_id)`, preventing duplicate registration for the same attendee and event.

## Relationship and deletion behaviour

- One organizer can own many events.
- One attendee can have many registrations.
- One event can have many registrations.
- An event/user referenced by a registration cannot be deleted through the protected foreign-key relationship.
- Event cancellation is a status change; it does not delete the event or its registrations.

## Booking capacity invariant

The event's `seat_limit` is the maximum allowed number of registration rows for that event.

The booking service performs a transaction and locks the event row before checking the current registration count and inserting a registration. This serializes booking attempts for one event in PostgreSQL. The unique constraint independently protects against duplicate attendee/event rows.

## Time handling

The configured project timezone is `Asia/Kolkata` and `USE_TZ=True`. Datetimes are stored in the database in Django's timezone-aware manner and rendered/handled in the configured local timezone.

## Migration history

Django migrations are the source of truth for schema changes. The production database was checked during deployment and all migrations reported as applied. To inspect migration state in a configured environment:

```powershell
python manage.py showmigrations
```

To apply pending migrations:

```powershell
python manage.py migrate --noinput
```
