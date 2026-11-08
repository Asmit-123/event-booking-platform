from accounts.models import User

PASSWORD = "Str0ng-Pass-9876"


def create_user(role=User.Role.ATTENDEE, email=None, username=None):
    """Create a throwaway user with made-up data for tests."""
    role = str(role)
    return User.objects.create_user(
        email=email or f"{role}@example.com",
        username=username or role,
        password=PASSWORD,
        first_name="Test",
        last_name=role.capitalize(),
        role=role,
    )