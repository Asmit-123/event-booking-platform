# Event Booking & RSVP Platform

A full-stack event booking application built with **Python, Django, PostgreSQL, and Bootstrap**. Organizers can publish and manage events; attendees can discover events and reserve seats. The application is deployed on **Vercel**, with **Neon** providing the managed PostgreSQL database.

## Live application

The production URL is managed by the Vercel project. Open the Vercel dashboard and use the current **Production** domain, since deployment URLs and aliases can change.

## Features

### Accounts and access
- Email-based account registration and login.
- Two account roles: **Organizer** and **Attendee**.
- Role-based access control for organizer and attendee pages.
- Login-attempt throttling to reduce repeated password-guessing attempts.

### Organizer features
- Create, edit, and cancel events.
- View an organizer dashboard with event and registration statistics.
- View the attendee list for an event.
- Export attendee data as CSV.
- Edit/cancellation rules prevent changes to past or cancelled events.
- Seat capacity cannot be reduced below the number of existing registrations.

### Attendee features
- Browse upcoming events and view event details.
- Search events by title, venue, or description.
- Filter by date range and availability.
- Register for events and view personal registrations.
- Download calendar event files (.ics).
- Registration confirmation email support when an SMTP provider is configured.

### Booking safeguards
- Only attendees can register for events.
- Duplicate registrations are prevented.
- Cancelled, started, and fully booked events cannot accept registrations.
- Capacity is checked on the server, not just in the browser.
- Database constraints protect important data invariants.
- Database transactions and row locking help prevent concurrent requests from exceeding event capacity.

## Technology stack

| Area | Technology |
|---|---|
| Backend | Python, Django |
| Database | PostgreSQL |
| Database hosting | Neon |
| Frontend | Django Templates, HTML, CSS, Bootstrap 5 |
| Deployment | Vercel |
| Source control | Git, GitHub |

## Application structure

The Django project is organized into three main domain apps:

- **accounts** — custom user model, email authentication, roles, permissions, and login throttling.
- **events** — event model, organizer workflows, event search/filtering, dashboard queries, CSV export, and calendar export.
- **registrations** — attendee registrations, booking business logic, and confirmation emails.

The `config` package contains Django project settings, WSGI/ASGI entry points, and root URL configuration. Templates and static assets provide the server-rendered user interface.

## Run locally

### Requirements
- Python version compatible with the Django version pinned in `requirements.txt`.
- Git.
- A PostgreSQL database (or a separately configured local development database).

### Setup on Windows PowerShell

1. Clone the repository:

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

4. Create a local environment file:

   ```powershell
   Copy-Item .env.example .env
   ```

5. Edit `.env` and provide valid local values for the required settings. At minimum, configure:
   - `SECRET_KEY` — a unique, random Django secret.
   - `DATABASE_URL` — a PostgreSQL connection URL.
   - `ALLOWED_HOSTS` — allowed local hostnames, such as `127.0.0.1,localhost`.

   Do not leave example placeholders in place. Never commit your real `.env` file or share its values publicly.

6. Apply database migrations and start Django:

   ```powershell
   python manage.py migrate
   python manage.py runserver
   ```

7. Visit **http://127.0.0.1:8000/**.

## Environment variables

The project reads configuration from environment variables (and a local `.env` file when present).

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Django signing and cryptographic key. Keep it private and use a high-entropy value. |
| `DATABASE_URL` | PostgreSQL database connection URL. |
| `ALLOWED_HOSTS` | Comma-separated list of allowed hostnames. |
| `DJANGO_SETTINGS_MODULE` | Production uses `config.settings.production`. |
| `CSRF_TRUSTED_ORIGINS` | Comma-separated trusted origins, including the scheme (for example, `https://example.com`). |
| `SECURE_HSTS_SECONDS` | Optional HSTS duration; production settings define a default. |
| `EMAIL_BACKEND` | Optional email backend. The project defaults to Django's console backend unless configured otherwise. |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | SMTP connection settings when using a real email provider. |
| `EMAIL_USE_TLS` | SMTP TLS option. |
| `DEFAULT_FROM_EMAIL` | Sender address for outgoing messages. |

Use a separate secret and database URL for each environment. Do not put credentials in source code, screenshots, README files, or GitHub issues.

## Production deployment: Vercel + Neon

This repository is connected to a Vercel project, while Neon hosts the production PostgreSQL database.

At a high level:

1. Create a PostgreSQL database in Neon.
2. Import this GitHub repository into Vercel and select `main` as the production branch.
3. Configure the required Production environment variables in Vercel:
   - `DJANGO_SETTINGS_MODULE=config.settings.production`
   - `SECRET_KEY`
   - `DATABASE_URL`
   - `ALLOWED_HOSTS`
   - `CSRF_TRUSTED_ORIGINS`
4. For the Vercel runtime, use Neon's **pooled** connection URL. The project disables Django server-side cursors for compatibility with transaction pooling.
5. Deploy the application.
6. Apply schema migrations from a trusted local terminal using Neon's **direct/unpooled** connection URL:

   ```powershell
   $env:DJANGO_SETTINGS_MODULE="config.settings.production"
   $env:DATABASE_URL="YOUR_NEON_DIRECT_CONNECTION_URL"
   $env:SECRET_KEY="YOUR_DJANGO_SECRET_KEY"
   $env:ALLOWED_HOSTS="YOUR_PRODUCTION_HOSTNAME"
   $env:CSRF_TRUSTED_ORIGINS="https://YOUR_PRODUCTION_HOSTNAME"

   python manage.py migrate --noinput
   python manage.py check --deploy
   ```

   Replace each placeholder locally; never paste real values into this README or commit them.
7. Ensure the production hostname is included in both `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`. If the Vercel domain changes, update these values and redeploy.
8. After changing Vercel environment variables, trigger a new deployment so the running deployment receives the updated configuration.

## Useful Django commands

```powershell
# Run local development server
python manage.py runserver

# Apply database migrations
python manage.py migrate

# Inspect migration status
python manage.py showmigrations

# Run standard project checks
python manage.py check

# Run production deployment checks
python manage.py check --deploy

# Collect static assets
python manage.py collectstatic --noinput
```

## Testing and demo preparation

For a project demonstration, prepare one organizer account and at least two attendee accounts. Create a disposable upcoming event with a small seat limit, then demonstrate event creation, discovery, booking, duplicate-booking rejection, capacity enforcement, attendee listing, and CSV/calendar exports.

A useful production smoke-test sequence is:

1. Confirm the homepage and event listing load over HTTPS.
2. Create an account and sign in.
3. Confirm role-restricted pages reject the wrong role.
4. Create an event as an organizer.
5. Register an attendee and confirm the seat count updates.
6. Attempt a duplicate registration and a registration after the event is full.
7. Verify organizer ownership restrictions and exports.
8. Check that static assets load and email behaviour matches the configured email backend.

Only mark a test as passed after actually running it in the target environment.

## Known operational notes

- Production email delivery requires a working SMTP provider and appropriate sender configuration. Without that, the default console backend is mainly useful for development.
- The production database is PostgreSQL on Neon. Use the pooled connection for normal application traffic and the direct connection for schema migrations.
- No demo passwords or production secrets are included in this repository.
- A Vercel deployment marked **Ready** confirms that the deployment build completed; it does not, by itself, prove every application workflow has been manually tested.

## License

No open-source license has been added yet. Unless a license is added, the repository's contents remain under the copyright holder's rights.
