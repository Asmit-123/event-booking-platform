# Technical Interview Preparation

This guide is a revision aid for explaining the project. Use it to understand and describe the code you actually built; do not memorize claims that you cannot demonstrate.

## 1. Project pitch

**Short version:**  
"I built a server-rendered event booking and RSVP platform using Python, Django and PostgreSQL. It has organizer and attendee roles. Organizers can publish and manage events, while attendees can discover events and register. I focused on enforcing booking rules on the backend, especially capacity and duplicate-registration protection, and deployed the application on Vercel with Neon PostgreSQL."

Be ready to demonstrate the live application and explain one real code path, especially the registration service.

## 2. Python fundamentals

Revise:
- Variables, primitive and collection types.
- Conditions, loops, functions and return values.
- Classes, instances, inheritance and composition.
- Exceptions and validation.
- Imports, modules, packages and virtual environments.
- Iterators, comprehensions and context managers.

Project connections:
- Django models and forms are Python classes.
- Service functions encapsulate operations.
- Exceptions such as `ValidationError` communicate rejected business operations.
- `with`/transaction decorators manage database transaction boundaries.

## 3. Django architecture

Know the responsibilities of:
- URL configuration: maps URL patterns to views.
- Views: coordinate request handling and responses.
- Templates: render server-side HTML.
- Forms: parse and validate user input.
- Models: define persisted data and relationships.
- ORM: translate Python query expressions into SQL.
- Middleware: run request/response processing around views.
- Settings: configure apps, middleware, database, security and deployment.

Be able to trace: browser request → URL resolver → middleware → view → form/service/selector → ORM/database → template or response.

## 4. ORM and PostgreSQL

Revise:
- Primary keys and foreign keys.
- One-to-many relationships.
- Unique and check constraints.
- Indexes and query plans.
- Transactions and atomicity.
- Row-level locks and isolation concepts.
- Aggregation with `Count`, computed expressions with `F`, and eager loading with `select_related`.

Project examples:
- An organizer owns many events.
- An event has many registrations.
- A registration belongs to one attendee and one event.
- A unique constraint on event/attendee prevents duplicate bookings.
- A positive-seat-limit check constraint protects event data.
- The event status/start-time index supports common event-list filtering.

## 5. Authentication and authorization

Explain the difference:
- **Authentication:** proving who the user is (login).
- **Authorization:** deciding what that authenticated user may do (role and ownership checks).

This project uses a custom Django user model with email as the login identifier and a role field for organizer/attendee. Role decorators protect role-specific views. Organizer queries also scope objects to the current organizer, so knowing another event's ID is not enough to edit it.

Password handling is delegated to Django's authentication system; do not describe passwords as plaintext.

## 6. Capacity and race conditions

**Question: Why is checking the seat count in a view not enough?**

If two requests arrive at nearly the same time for the last seat, both can read the same available count before either inserts. Both might then book, exceeding capacity. This is a race condition.

**How does this project address it?**

The registration service uses `transaction.atomic` and `select_for_update()` on the event row. PostgreSQL serializes transactions attempting to lock that same event row. Each transaction checks duplicate registration and capacity after obtaining the lock, then inserts the registration. The database unique constraint is an additional guard against duplicate attendee/event pairs.

Be precise: row locking protects the booking path when all competing operations follow the same locking discipline and the database supports row locks. This is why PostgreSQL is used in production.

## 7. Security

Be prepared to explain:
- Why `DEBUG=False` in production.
- Why `SECRET_KEY` and `DATABASE_URL` belong in environment variables.
- `ALLOWED_HOSTS` versus `CSRF_TRUSTED_ORIGINS`.
- CSRF protection on state-changing forms.
- HTTPS redirect and secure cookies.
- HSTS and why subdomain/preload settings need domain ownership.
- Role checks and object ownership checks.
- Login-attempt throttling.
- Why CSV exports are restricted to the owning organizer and marked non-cacheable.
- Why production secrets must never be committed or pasted into public issues.

## 8. Testing and quality

Be ready to describe:
- What unit tests validate (small functions/services).
- What integration tests validate (views, database constraints, full workflows).
- Why booking capacity needs tests at the exact boundary: one seat left, full event, duplicate user, cancelled event and past event.
- Why concurrency tests should run against PostgreSQL rather than assuming SQLite reproduces row locks.
- How to run Django checks:

```powershell
python manage.py check
python manage.py check --deploy
python manage.py showmigrations
```

Do not claim comprehensive test coverage unless you have inspected and run the test suite. Capture actual test results before presenting them.

## 9. Deployment

Explain the roles:
- GitHub stores source code and history.
- Vercel builds and hosts the Django application from the connected repository.
- Neon hosts managed PostgreSQL.
- Environment variables provide per-environment configuration.
- Static assets are collected into `STATIC_ROOT`.
- The pooled Neon URL is used for runtime traffic; the direct/unpooled URL is used for migrations.
- Migrations evolve the database schema; they are not the same as deploying application code.

Useful commands:

```powershell
python manage.py migrate --noinput
python manage.py check --deploy
python manage.py showmigrations
```

## 10. Questions to practise aloud

1. Why did you choose Django for this application?
2. What is the difference between a Django model and a form?
3. What does the ORM do?
4. Why use a custom user model instead of Django's default user unchanged?
5. What is the difference between authentication and authorization?
6. How do the organizer and attendee roles differ?
7. How is event ownership enforced?
8. How do you prevent duplicate registrations?
9. What is a race condition, and how could it overbook an event?
10. What do `transaction.atomic` and `select_for_update` do?
11. Why do you need both application checks and database constraints?
12. What is a foreign key, and why use `PROTECT` for these relationships?
13. What is an index, and which queries benefit from the event index?
14. What is the difference between `ALLOWED_HOSTS` and CSRF trusted origins?
15. Why use a pooled database URL at runtime and a direct URL for migrations?
16. What does `collectstatic` do?
17. How would you test that capacity cannot be exceeded?
18. What would you improve if the application had ten times more users?

## 11. Honest improvement areas

Potential next steps, depending on observed needs:
- Expand automated tests for PostgreSQL transaction/concurrency behaviour.
- Add monitoring and alerting.
- Configure and verify production SMTP delivery.
- Add background processing if email delivery needs retries or should not run in the request cycle.
- Review rate-limit persistence and trusted-proxy configuration against the final hosting topology.
- Add a custom domain and matching production security configuration if desired.

In an interview, distinguish implemented functionality from future improvements. That honesty is stronger than claiming features that are not in the repository.
