from .base import *  # noqa: F401,F403
from .base import env

DEBUG = False

# No defaults: the app refuses to start if these are not configured.
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

# The host terminates HTTPS and reports the original scheme in this header.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# HSTS makes browsers insist on HTTPS. It is sticky, so start short and raise it later.
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=3600)

# Deliberately not enabled: includeSubDomains and preload only make sense on a domain we own,
# and we deploy on the host's shared domain.
SILENCED_SYSTEM_CHECKS = ["security.W005", "security.W021"]

# Logs go to standard output, which the host collects. Django never logs request bodies,
# so passwords and tokens stay out of the logs.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"simple": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "simple"}},
    "root": {"handlers": ["console"], "level": "WARNING"},
}