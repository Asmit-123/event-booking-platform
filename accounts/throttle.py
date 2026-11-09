import ipaddress
from datetime import timedelta
from functools import wraps

from django.conf import settings
from django.shortcuts import render
from django.utils import timezone

from .models import LoginAttempt

WINDOW = timedelta(minutes=15)
MAX_FAILURES_PER_EMAIL_AND_IP = 5
MAX_FAILURES_PER_IP = 20


def client_ip(request):
    """The client's address, trusting only as many proxy hops as configured."""
    remote = request.META.get("REMOTE_ADDR", "0.0.0.0")
    hops = settings.TRUSTED_PROXY_COUNT
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if hops <= 0 or not forwarded:
        return remote

    addresses = [part.strip() for part in forwarded.split(",") if part.strip()]
    if len(addresses) < hops:
        return remote

    candidate = addresses[-hops]
    try:
        ipaddress.ip_address(candidate)
    except ValueError:
        return remote
    return candidate


def _recent_failures(ip):
    return LoginAttempt.objects.filter(ip_address=ip, created_at__gte=timezone.now() - WINDOW)


def is_locked(request, email):
    recent = _recent_failures(client_ip(request))
    return (
        recent.count() >= MAX_FAILURES_PER_IP
        or recent.filter(email=email).count() >= MAX_FAILURES_PER_EMAIL_AND_IP
    )


def record_failure(request, email):
    LoginAttempt.objects.filter(created_at__lt=timezone.now() - WINDOW).delete()
    LoginAttempt.objects.create(ip_address=client_ip(request), email=email[:254])


def clear_failures(request, email):
    LoginAttempt.objects.filter(ip_address=client_ip(request), email=email).delete()


def throttle_logins(view):
    """Refuse login POSTs from a locked client and count failed attempts."""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if request.method != "POST":
            return view(request, *args, **kwargs)

        email = request.POST.get("username", "").strip().lower()
        if is_locked(request, email):
            response = render(request, "429.html", status=429)
            response["Retry-After"] = str(int(WINDOW.total_seconds()))
            return response

        response = view(request, *args, **kwargs)
        if response.status_code == 200:
            record_failure(request, email)
        else:
            clear_failures(request, email)
        return response

    return wrapper