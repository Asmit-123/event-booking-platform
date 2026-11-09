import logging

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

logger = logging.getLogger(__name__)


def send_registration_confirmation(registration):
    """Email the attendee a booking confirmation.

    Never raises: a mail outage must not undo or fail a completed booking.
    """
    event = registration.event
    attendee = registration.attendee
    start = timezone.localtime(event.start_datetime).strftime("%A, %d %B %Y, %H:%M")
    subject = f"You're registered: {' '.join(event.title.split())}"
    body = (
        f"Hi {attendee.first_name},\n\n"
        f"You are registered for {event.title}.\n\n"
        f"When: {start} (Asia/Kolkata)\n"
        f"Where: {event.venue}\n\n"
        "See you there!\n"
    )
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [attendee.email])
    except Exception:
        logger.exception("Could not send confirmation email for registration %s", registration.pk)