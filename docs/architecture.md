# Architecture and Technical Design Decisions

## 1. High-level structure

The application follows a server-rendered Django architecture. The browser requests a Django URL; the matching view validates input, invokes domain services/selectors, and renders a Django template or returns a file response. Django's ORM communicates with PostgreSQL.

```text
Browser
  |
  | HTTP / HTTPS
  v
Vercel deployment
  |
  v
Django project (config)
  |-- accounts       Authentication, custom user, roles, permissions
  |-- events         Event lifecycle, discovery, organizer tools, exports
  |-- registrations  Booking workflow, attendee registrations, email
  |
  v
Django ORM
  |
  v
Neon PostgreSQL
```

Static assets are collected into `STATIC_ROOT` for the deployment platform's static-file handling. Django templates render the HTML; Bootstrap provides the UI styling.

## 2. Repository layout

- `config/settings/base.py`: shared settings, installed apps, middleware, templates, database, static assets, email defaults, and common security headers.
- `config/settings/production.py`: production-only settings such as `DEBUG=False`, allowed hosts, CSRF origins, HTTPS redirects, secure cookies, HSTS, and console logging.
- `config/urls.py`: root URL routing and admin login throttling.
- `accounts/`: custom user model, signup/login forms, role decorators, login-attempt model and throttling.
- `events/`: event model, forms, validators, service operations, query selectors, dashboard, CSV export and ICS calendar export.
- `registrations/`: registration model, booking service, attendee registration views and confirmation email.
- `templates/` and `static/`: server-rendered UI and static assets.

## 3. Request and domain boundaries

Views are intentionally thin: they translate HTTP requests into calls to application logic and choose the response. Forms validate submitted input. Service functions implement operations that must enforce business rules. Selectors encapsulate reusable ORM queries and annotations.

Examples:
- `events.services.create_event` validates organizer role, future start time and model fields.
- `events.services.update_event` locks the event row, verifies ownership and lifecycle state, and prevents reducing capacity below existing registrations.
- `registrations.services.register_for_event` locks the event row and validates role, event state, duplicate registration and available capacity before creating a registration.

This separation makes the business rules easier to test and reduces the risk of relying on frontend-only validation.

## 4. Authentication and authorization

The project defines `accounts.User`, extending Django's `AbstractUser`. Email is the login identifier and is unique; the user has exactly one application role: `organizer` or `attendee`.

Role decorators protect views:
- Anonymous users are redirected to login.
- Authenticated users with the wrong role receive a permission-denied response.
- Organizer event operations additionally filter the target event by the current organizer, preventing one organizer from modifying another organizer's event.

The login throttling middleware/helper records failed attempts by IP and email over a 15-minute window. It applies limits of five failures for an IP/email pair and twenty failures for an IP. The client-IP helper only uses forwarded addresses when a trusted proxy count is configured.

## 5. Booking integrity and concurrency

A naive capacity check can fail under concurrent requests: two attendees could both read the last available seat before either writes a registration.

The booking service therefore runs inside `transaction.atomic` and obtains the event row using `select_for_update()`. Requests attempting to book the same event serialize around that row lock. Within the transaction, the service checks:
1. The requester is an attendee.
2. The event is not cancelled.
3. The event has not started.
4. The attendee has not already registered.
5. The current registration count is below the seat limit.

A database `UniqueConstraint(event, attendee)` independently prevents duplicate attendee/event registrations. The event model also has a positive-seat-limit check constraint. Event update and cancellation services use row locks as well.

**Important:** row-level locking requires a database backend with appropriate transaction/locking support; production uses PostgreSQL. SQLite-based local test configurations, if used, do not reproduce PostgreSQL's row-locking behaviour.

## 6. Data access and performance

Selectors use ORM annotations such as `Count` and `F` expressions to calculate seats taken and remaining. `select_related` is used where related objects are needed, such as organizer or attendee data. Event listings are paginated at nine events per page.

The database includes an index on event status and start time, plus indexes on login-attempt lookup fields. The Neon pooled runtime connection has Django server-side cursors disabled because transaction pooling does not support them reliably.

## 7. Production security choices

- `DEBUG=False` in production.
- `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` are supplied through environment variables.
- HTTPS redirect and secure session/CSRF cookies are enabled in production.
- HSTS starts with a one-hour default; raise it only after validating the domain and HTTPS setup.
- Common response protections include clickjacking protection, content-type sniffing protection, referrer policy and Content Security Policy.
- Request body size is limited.
- Secrets and database credentials are not stored in source control.
- Login attempts are throttled.
- Organizer-only CSV exports are protected by authentication, role and ownership checks and are marked `never_cache`.

The two silenced deployment checks in production settings concern HSTS subdomain/preload configuration. They are intentionally not enabled for a shared platform hostname; do not enable them blindly without a domain you control and a reviewed rollout plan.

## 8. Database hosting and deployment

Vercel hosts the Django application. Neon hosts PostgreSQL. The app uses environment variables rather than hard-coded production credentials.

- Runtime: Neon pooled connection URL.
- One-off migrations: Neon direct/unpooled connection URL.
- `DISABLE_SERVER_SIDE_CURSORS=True` is configured for the runtime database connection.
- Vercel is connected to the GitHub repository and production branch. A new production deployment is created from changes merged/pushed to that branch.
- Django's static collection output is directed to `staticfiles/`.

## 9. Technical design decisions

| Decision | Reason |
|---|---|
| Django server-rendered templates | Keeps the stack cohesive and avoids a separate frontend/API deployment for this project's scope. |
| Custom user model from the start | Supports email as the unique login identifier and a first-class role field. |
| PostgreSQL | Provides relational integrity, transactions, constraints and row-level locking needed for booking capacity. |
| Neon | Managed PostgreSQL that separates database hosting from application hosting. |
| Service functions | Centralize multi-step business rules so they are not duplicated across views. |
| Selectors | Keep reusable query construction and annotations out of view code. |
| Database constraints | Enforce key invariants even if application code has a bug or two requests race. |
| Row locks and atomic transactions | Serialize bookings and event changes to protect capacity and lifecycle rules. |
| Vercel | Provides Git-connected deployment and hosting for the Django application. |
| Environment-based configuration | Keeps secrets and environment-specific settings outside committed code. |

## 10. Areas to revisit as the project grows

- Add/expand automated integration tests against PostgreSQL for concurrent booking and capacity boundaries.
- Configure a production SMTP provider and verify delivery, bounce handling and sender-domain authentication.
- Add monitoring/alerting for application errors, database connectivity and email failures.
- Consider background task processing if email or other work becomes slow or needs retries.
- Review rate-limiting storage and proxy trust settings for the final hosting topology.
- Add a custom domain only with matching host, CSRF and HTTPS configuration.
