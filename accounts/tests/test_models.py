from django.test import TestCase

from accounts.models import User

from .helpers import PASSWORD, create_user


class UserModelTests(TestCase):
    def test_email_is_lowercased_on_save(self):
        user = create_user(email="Mixed@Example.COM")
        user.refresh_from_db()
        self.assertEqual(user.email, "mixed@example.com")

    def test_password_is_hashed(self):
        user = create_user()
        self.assertNotEqual(user.password, PASSWORD)
        self.assertTrue(user.password.startswith("pbkdf2_sha256$"))
        self.assertTrue(user.check_password(PASSWORD))

    def test_role_helpers(self):
        organizer = create_user(User.Role.ORGANIZER)
        attendee = create_user(User.Role.ATTENDEE)
        self.assertTrue(organizer.is_organizer)
        self.assertFalse(organizer.is_attendee)
        self.assertTrue(attendee.is_attendee)
        self.assertFalse(attendee.is_organizer)