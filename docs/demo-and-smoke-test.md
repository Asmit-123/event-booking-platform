# Demo Walkthrough and Production Smoke Tests

Use this checklist before a project review, portfolio walkthrough or interview demonstration. Run destructive actions only with disposable demo events/accounts.

## Prepare demo data

Create the following accounts through the signup page:

- **Organizer:** one account with the organizer role.
- **Attendee A:** a normal attendee account.
- **Attendee B:** a second attendee account to demonstrate capacity and multi-user behaviour.

Create a disposable event with:
- A clear title and description.
- A venue.
- A future date/time in Asia/Kolkata.
- A small seat limit (for example, two seats).

Do not put demo passwords, real user data, API keys or database credentials in this repository. Share temporary demo credentials through a private channel if a reviewer needs them.

## Suggested 5–8 minute walkthrough

1. Open the public homepage and event listing.
2. Demonstrate search, date filtering and the available-seats filter.
3. Log in as the organizer and create an event.
4. Open the organizer dashboard and show event/registration statistics.
5. Open the event attendee list and demonstrate CSV export.
6. Log out and log in as Attendee A; register for the event.
7. Show the attendee's personal registrations and the event's updated seat count.
8. Register Attendee B if a second seat is available.
9. Show that a repeat registration is rejected and that a full event cannot accept another attendee.
10. Show the event's calendar (.ics) download.
11. If SMTP is configured, demonstrate the confirmation email; otherwise explain that local development uses the console backend and production email requires SMTP configuration.

## Production smoke-test checklist

### Public pages
- [ ] Homepage loads over HTTPS.
- [ ] Event list loads and is paginated.
- [ ] Event detail page loads.
- [ ] Search by title/venue/description works.
- [ ] Date range and available-only filters work.
- [ ] Calendar file download returns a valid .ics file.

### Accounts and permissions
- [ ] New attendee account can be created.
- [ ] User can log in using email and password.
- [ ] User can log out.
- [ ] Anonymous user is redirected to login for protected pages.
- [ ] Attendee cannot access organizer dashboard/actions.
- [ ] Organizer cannot use attendee-only registration actions.
- [ ] Organizer can manage only their own events.

### Organizer event lifecycle
- [ ] Organizer can create an upcoming event.
- [ ] Organizer can edit their own upcoming event.
- [ ] Organizer cannot edit a past or cancelled event.
- [ ] Organizer can cancel an upcoming event.
- [ ] Cancelled events are not bookable.
- [ ] Seat limit cannot be reduced below the number already registered.
- [ ] Dashboard totals and fill rate update as expected.
- [ ] Organizer can view attendees and export the CSV.

### Registration integrity
- [ ] Attendee can register for an active upcoming event with seats available.
- [ ] Duplicate registration is rejected.
- [ ] Registration for a full event is rejected.
- [ ] Registration for a cancelled event is rejected.
- [ ] Registration for a past/started event is rejected.
- [ ] Seat count updates after successful registration.
- [ ] If testing concurrency, use two separate sessions/users against PostgreSQL and verify the seat limit is never exceeded.

### Production configuration
- [ ] `DEBUG=False` is active in production.
- [ ] Production hostname is included in `ALLOWED_HOSTS`.
- [ ] HTTPS origin is included in `CSRF_TRUSTED_ORIGINS`.
- [ ] HTTPS redirect and secure cookies work.
- [ ] Static assets load correctly.
- [ ] Email behaviour matches the configured backend.
- [ ] No secret values appear in browser output, logs, Git history or screenshots.

## Record test evidence

For a review, record:
- Date and environment tested (production/staging/local).
- Browser/device used.
- Test case and result (pass/fail/not tested).
- Sanitized screenshot or short screen recording where useful.
- Any defect found and its follow-up issue.

Do not claim a test passed unless you personally ran it in the target environment. A deployment being marked READY confirms the deployment build completed; it does not prove every user workflow has been tested.
