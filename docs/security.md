# Security

## Checklist (from the project brief)

| Item | How it is done | Evidence |
|------|----------------|----------|
| CSRF protection | `CsrfViewMiddleware`, a token in every POST form, CSRF cookie `HttpOnly` and `SameSite=Lax`, friendly CSRF failure page | `RegisterViewTests.test_post_without_a_csrf_token_is_rejected`, `EventCancelViewTests.test_post_without_a_csrf_token_is_rejected`, `CookieFlagTests` |
| Password hashing | Django's salted PBKDF2 hashes; Django's password validators on sign-up | `UserModelTests.test_password_is_hashed`, `SignUpTests.test_weak_password_is_rejected` |
| Input validation | Forms plus `full_clean()` in every service; length limits; integer URL converters; request body limit of 256 KiB | `test_edge_cases.py`, `test_input_limits.py` |
| Authorization checks | Role decorators, owner-filtered queries (404 for other people's events), role and ownership re-checked in services | `test_access_matrix.py`, `test_permissions.py`, the ownership tests in `events/tests` |
| Environment variable protection | `django-environ`; no defaults for `SECRET_KEY` and `DATABASE_URL`; `.env` ignored by Git; history scanned | Secret-leak scan (Phase 8, Task 7) |
| Secure session handling | Database sessions, `HttpOnly`, `SameSite=Lax`, 7-day lifetime, `Secure` and HTTPS redirect in production, session key rotated at login (Django) | `CookieFlagTests`, `check --deploy` |
| Database constraints | `CHECK`, `UNIQUE`, `PROTECT` foreign keys | `test_models.py`, `docs/business-rules.md`, the integrity audit |
| Login rate limiting | Database-backed throttle for site and admin login: 5 failures per address and email, 20 per address, 15-minute window | `test_throttle.py` |
| Protection against unauthorized data access | Attendee list and event management are owner-only (404 otherwise); My registrations is filtered by the logged-in user | `EventAttendeesViewTests`, `MyRegistrationsViewTests` |
| Browser hardening | Content Security Policy (own origin only), `X-Frame-Options: DENY`, `nosniff`, referrer policy, self-hosted assets | `test_security_headers.py` |

## Decisions

- Rate-limit state lives in the database so it is shared by all worker processes and survives restarts.
- The client address is read from `X-Forwarded-For` only as far as `TRUSTED_PROXY_COUNT` allows, because entries further left are client-controlled.
- Bootstrap is self-hosted, so no third party can change code that runs in our pages and the CSP can stay strict.

## Known limitations

- No multi-factor authentication and no email verification (not required by the specification).
- Rate limiting is approximate under simultaneous attempts.
- `TRUSTED_PROXY_COUNT` must match the real number of proxies in front of the app, or the address used for throttling will be wrong.
- Self-hosted Bootstrap must be updated by hand when security fixes are released.
- HSTS is set to a short lifetime by default and should be raised once HTTPS is confirmed working.