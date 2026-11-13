from datetime import date

from django import forms
from django.core.validators import MaxValueValidator, MinValueValidator

from accounts.forms import BootstrapFormMixin

from .models import Event
from .validators import validate_start_in_future


class EventForm(BootstrapFormMixin, forms.ModelForm):
    """Input form for creating or editing an event."""

    use_registration_deadline = forms.BooleanField(
        required=False,
        label="Set a registration deadline",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    class Meta:
        model = Event
        fields = (
            "title", "description", "venue", "start_datetime",
            "registration_deadline", "seat_limit",
        )
        labels = {
            "start_datetime": "Date and time",
            "registration_deadline": "Registration closes on",
            "seat_limit": "Seat limit",
        }
        help_texts = {
            "start_datetime": "Entered and shown in Asia/Kolkata time.",
            "registration_deadline": "Must be earlier than the event start time.",
        }
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
            "start_datetime": forms.DateTimeInput(
                attrs={"type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "registration_deadline": forms.DateTimeInput(
                attrs={"type": "datetime-local", "disabled": True},
                format="%Y-%m-%dT%H:%M",
            ),
            "seat_limit": forms.NumberInput(attrs={"min": 1}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.registration_deadline:
            self.initial["use_registration_deadline"] = True
            self.fields["registration_deadline"].widget.attrs.pop("disabled", None)

    def clean_start_datetime(self):
        start_datetime = self.cleaned_data["start_datetime"]
        validate_start_in_future(start_datetime)
        return start_datetime

    def clean(self):
        cleaned = super().clean()
        enabled = cleaned.get("use_registration_deadline", False)
        deadline = cleaned.get("registration_deadline")
        start = cleaned.get("start_datetime")

        if enabled and not deadline:
            self.add_error("registration_deadline", "Enter a registration deadline or uncheck this option.")
        elif not enabled:
            cleaned["registration_deadline"] = None
        elif deadline and start and deadline >= start:
            self.add_error(
                "registration_deadline",
                "The registration deadline must be before the event start time.",
            )
        return cleaned


FILTER_MIN_DATE = date(2000, 1, 1)
FILTER_MAX_DATE = date(2100, 12, 31)


def _date_filter_field(label):
    return forms.DateField(
        required=False,
        label=label,
        validators=[MinValueValidator(FILTER_MIN_DATE), MaxValueValidator(FILTER_MAX_DATE)],
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
    )


class EventSearchForm(forms.Form):
    """Validates the filters on the public event list (read from the query string)."""

    q = forms.CharField(
        required=False,
        max_length=100,
        label="Search events",
        widget=forms.TextInput(
            attrs={
                "type": "search",
                "class": "form-control",
                "placeholder": "Search by title, venue or keyword",
            }
        ),
    )
    date_from = _date_filter_field("From")
    date_to = _date_filter_field("To")
    available_only = forms.BooleanField(
        required=False,
        label="Only show events with seats left",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    def clean(self):
        cleaned = super().clean()
        date_from = cleaned.get("date_from")
        date_to = cleaned.get("date_to")
        if date_from and date_to and date_to < date_from:
            self.add_error("date_to", "The end date cannot be before the start date.")
        return cleaned
