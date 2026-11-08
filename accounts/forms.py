from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import User


def add_bootstrap_classes(form):
    """Give every non-radio widget Bootstrap's input styling."""
    for field in form.fields.values():
        if not isinstance(field.widget, forms.RadioSelect):
            field.widget.attrs["class"] = "form-control"


class SignUpForm(UserCreationForm):
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        add_bootstrap_classes(self)

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email


class EmailAuthenticationForm(AuthenticationForm):
    """Login form: email + password, with a deliberately generic error."""

    username = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={"autofocus": True}),
    )

    error_messages = {
        "invalid_login": "Incorrect email or password.",
        "inactive": "This account is inactive.",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        add_bootstrap_classes(self)

    def clean_username(self):
        return self.cleaned_data["username"].lower()