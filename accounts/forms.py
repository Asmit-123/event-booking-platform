from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import User


def bootstrap_class(widget):
    """The Bootstrap 5 class that fits a form widget."""
    if isinstance(widget, (forms.RadioSelect, forms.CheckboxInput)):
        return "form-check-input"
    if isinstance(widget, forms.Select):
        return "form-select"
    return "form-control"


class BootstrapFormMixin:
    """Styles widgets with Bootstrap and marks fields invalid as soon as they get an error."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = bootstrap_class(field.widget)

    def add_error(self, field, error):
        super().add_error(field, error)
        for name in self.errors:
            if name not in self.fields:
                continue
            widget = self.fields[name].widget
            if "is-invalid" not in widget.attrs["class"]:
                widget.attrs["class"] += " is-invalid"
                widget.attrs["aria-invalid"] = "true"


class SignUpForm(BootstrapFormMixin, UserCreationForm):
    """Sign-up form: validates input and stores a hashed password."""

    role = forms.ChoiceField(
        choices=User.Role.choices,
        widget=forms.RadioSelect,
        error_messages={
            "required": "Please choose whether you are an organizer or an attendee.",
        },
    )

    class Meta:
        model = User
        fields = ("email", "username", "first_name", "last_name", "role")

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email


class EmailAuthenticationForm(BootstrapFormMixin, AuthenticationForm):
    """Login form: email + password, with a deliberately generic error."""

    username = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={"autofocus": True}),
    )

    error_messages = {
        "invalid_login": "Incorrect email or password.",
        "inactive": "This account is inactive.",
    }

    def clean_username(self):
        return self.cleaned_data["username"].lower()