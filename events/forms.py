from django import forms

from .models import Event
from .validators import validate_start_in_future


class EventForm(forms.ModelForm):
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
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
            "venue": forms.TextInput(attrs={"class": "form-control"}),
            "start_datetime": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "seat_limit": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
        }

    def clean_start_datetime(self):
        start_datetime = self.cleaned_data["start_datetime"]
        validate_start_in_future(start_datetime)
        return start_datetime