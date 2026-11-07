from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import User


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
        for field in self.fields.values():
            if not isinstance(field.widget, forms.RadioSelect):
                field.widget.attrs["class"] = "form-control"

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email