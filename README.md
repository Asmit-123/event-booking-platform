# Event Booking & RSVP Platform

A Django web application for publishing events and managing attendee registrations. It supports two account roles—organizers and attendees—and enforces booking rules on the server side.

**Production:** deployed on Vercel  
**Database:** PostgreSQL hosted by Neon  
**Repository:** https://github.com/Asmit-123/event-booking-platform

> The production hostname can change if the Vercel project/domain configuration changes. Use the Production domain shown in the Vercel project dashboard.

## Features

### Accounts and access
- Sign up and log in using email.
- Each account has one role: organizer or attendee.
- Role-based view protection for organizer and attendee workflows.
- Login-attempt throttling to slow repeated password guessing.

### Organizer workflows
- Create, edit, and cancel events.
- View an organizer dashboard with event and registration statistics.
- View the attendee list for an event.
- Export an event's attendee list as CSV.
- Edit/cancel restrictions protect past and cancelled events; seat limits cannot be reduced below current registrations.

### Attendee workflows
- Browse and view upcoming events.
- Search by title, venue, or description; filter by date and remaining availability.
- Register for an event and view personal registrations.
- Download an event calendar file (.ics).
- Receive a registration confirmation email when production email delivery is configured.

### Booking rules
- Only attendees can register; only organizers can manage their own events.
- No duplicate registration for the same attendee/event pair.
- No registration for cancelled or already-started events.
- Event capacity is checked on the server, with a database row lock around booking.
- Database constraints provide a second line of defence against duplicate registrations and invalid seat limits.

## Technology stack

| Layer | Technology |
|---|---|
| Language | Python |
| Web framework | Django |
| Database | PostgreSQL |
| Managed database hosting | Neon |
| Frontend | Django Templates, HTML, CSS, Bootstrap |
| Application hosting | Vercel |
| Version control | Git and GitHub |

The application is a server-rendered Django project; it does not require a separate React/Next.js frontend.

## Application architecture

The repository separates Django configuration from three domain apps:

- `accounts`: custom user model, email authentication, roles, permissions, and login throttling.
- `events`: event model, organizer workflows, discovery/search, dashboard selectors, CSV export, and calendar export.
- `registrations`: registration model, attendee workflows, booking service, and confirmation email.

Business operations are kept in service functions (for example, `registrations.services.register_for_event`). Query-focused code is kept in selectors. Django views handle HTTP requests, forms validate input, and models/database constraints protect persisted data.

See [Architecture and design decisions](docs/architecture.md) and [Database schema](docs/database-schema.md).

## Prerequisites

- Python compatible with the pinned Django version in `requirements.txt`.
- Git.
- A PostgreSQL database. For production, this project uses Neon.
- PowerShell examples below are written for Windows.

## Local installation

1. Clone the repository and enter the project directory:

   ```powershell
   git clone https://github.com/Asmit-123/event-booking-platform.git
   cd event-booking-platform
   ```

2. Create and activate a virtual environment:

   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

3. Install dependencies:

   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. Create a local `.env` file by copying the example:

   ```powershell
   Copy-Item .env.example .env
   ```

5. Edit `.env` and set a fresh secret key and a PostgreSQL connection URL. Example variable names are documented in [Environment configuration](#environment-configuration). Do not use the placeholder values from `.env.example`.

6. Apply migrations and start the development server:

   ```powershell
   python manage.py migrate
   python manage.py runserver
   ```

7. Open `http://127.0.0.1:8000/` in your browser.

For local development, Django's console email backend is the default; generated emails are printed in the terminal.

## Environment configuration

The application reads environment variables through `django-environ`. The following variables are used by the project:

| Variable | Required | Purpose |
|---|---:|---|
| `SECRET_KEY` | Yes | Django cryptographic signing key. Generate a unique, high-entropy value. |
| `DATABASE_URL` | Yes | PostgreSQL connection URL. |
| `ALLOWED_HOSTS` | Yes in production | Comma-separated allowed hostnames. |
| `DJANGO_SETTINGS_MODULE` | Production | Set to `config.settings.production`. |
| `CSRF_TRUSTED_ORIGINS` | Production when needed | Comma-separated trusted HTTPS origins. |
| `TRUSTED_PROXY_COUNT` | No | Number of trusted proxy hops used by login throttling; defaults to `0`. |
| `SECURE_HSTS_SECONDS` | No | HSTS duration; production default is `3600`. |
| `EMAIL_BACKEND` | No | Defaults to Django's console backend. Set SMTP backend for production email. |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | SMTP only | SMTP server credentials and settings. |
| `EMAIL_USE_TLS` | No | SMTP TLS setting; defaults to `True`. |
| `DEFAULT_FROM_EMAIL` | No | Sender address shown in outgoing mail. |

Never commit a real `.env` file, database URL, SMTP password, or `SECRET_KEY`. Configure production values in Vercel Project Settings → Environment Variables. Use Neon's pooled connection URL for Vercel runtime traffic. Use the direct/unpooled URL for one-off migrations.

The project includes `.env.example` with safe placeholders.

## Deployment (Vercel + Neon)

The production deployment uses the GitHub repository connected to a Vercel project and a Neon PostgreSQL database.

1. Create a Neon PostgreSQL database and copy its connection URLs.
2. In Vercel, import this GitHub repository and use `main` as the production branch.
3. Add production environment variables in Vercel:
   - `DJANGO_SETTINGS_MODULE=config.settings.production`
   - `SECRET_KEY` (unique secret)
   - `DATABASE_URL` (Neon pooled connection URL)
   - `ALLOWED_HOSTS` (the production hostname(s), comma-separated)
   - `CSRF_TRUSTED_ORIGINS` (matching HTTPS origin(s), comma-separated)
4. Deploy the production branch. Vercel detects the Django project; a custom `vercel.json` is not required for the current setup.
5. Apply database migrations using the Neon direct/unpooled URL from a trusted local terminal:

   ```powershell
   $env:DJANGO_SETTINGS_MODULE="config.settings.production"
   $env:DATABASE_URL="YOUR_NEON_DIRECT_CONNECTION_URL"
   $env:SECRET_KEY="YOUR_DJANGO_SECRET_KEY"
   $env:ALLOWED_HOSTS="YOUR_PRODUCTION_HOSTNAME"
   $env:CSRF_TRUSTED_ORIGINS="https://YOUR_PRODUCTION_HOSTNAME"
   python manage.py migrate --noinput
   ```

   The command above is a template: replace every placeholder locally. Never paste credentials into source control or issue trackers. Keep the pooled URL in Vercel for application runtime.
6. Check the production configuration with `python manage.py check --deploy`.
7. After changing production environment variables, trigger a new deployment so the deployment uses the updated values.
8. Test the live workflows using [the smoke-test checklist](docs/demo-and-smoke-test.md).

Vercel's deployment settings and domain assignments are managed in the Vercel dashboard. Confirm the exact current production domain there before setting `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`.

## Demo accounts and presentation

No public demo passwords are stored in this repository. For a presentation, create one organizer account and at least two attendee accounts through the signup flow, or prepare them in a controlled demo environment. Keep demo credentials private and rotate/delete them after the demonstration.

Use [Demo and smoke-test checklist](docs/demo-and-smoke-test.md) to prepare a repeatable walkthrough.

## Known limitations and operational notes

- Production email delivery depends on valid SMTP configuration and a verified sender/domain. Without SMTP settings, the default console backend is intended for local development.
- The app uses Django's built-in authentication/session framework; there is no separate OAuth/social-login provider configured.
- The production database is Neon PostgreSQL; the runtime uses its pooled connection. One-off schema migrations should use the direct connection URL.
- The deployment currently uses the Vercel-provided hostname unless a custom domain is configured. Update host and CSRF settings whenever the production domain changes.
- This README does not publish demo credentials or operational secrets. Supply them securely for a live demonstration.

## Project documentation

- [Architecture and technical design decisions](docs/architecture.md)
- [Database schema](docs/database-schema.md)
- [Demo walkthrough and smoke-test checklist](docs/demo-and-smoke-test.md)
- [Technical interview preparation](docs/interview-preparation.md)

## License

No license has been specified in this repository. All rights remain with the copyright holder unless a license is added.
