from django import forms

from accounts.forms import BootstrapFormMixin

from .models import Event
from .validators import validate_start_in_future


class EventForm(BootstrapFormMixin, forms.ModelForm):
    """Input form for creating or editing an event."""

    class Meta:
        model = Event
        fields = ("title", "description", "venue", "start_datetime", "seat_limit")
        labels = {
            "start_datetime": "Date and time",
            "seat_limit": "Seat limit",
        }
        help_texts = {
            "start_datetime": "Entered and shown in Asia/Kolkata time.",
        }
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
            "start_datetime": forms.DateTimeInput(
                attrs={"type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "seat_limit": forms.NumberInput(attrs={"min": 1}),
        }

    def clean_start_datetime(self):
        start_datetime = self.cleaned_data["start_datetime"]
        validate_start_in_future(start_datetime)
        return start_datetime