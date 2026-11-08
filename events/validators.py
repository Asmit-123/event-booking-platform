from django.core.exceptions import ValidationError
from django.utils import timezone


def validate_start_in_future(value):
    """Rule 4: an event must start in the future."""
    if value <= timezone.now():
        raise ValidationError(
            "The event must start in the future.", code="start_in_past"
        )