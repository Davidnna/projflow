from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Role, RoleCode, UserRole

User = get_user_model()


class UserModelTests(TestCase):
    def test_user_email_is_normalised(self):
        user = User.objects.create_user(
            email="  David.Example@Example.COM ",
            password="Strong-test-password-123",
        )
        self.assertEqual(user.email, "david.example@example.com")

    def test_user_password_is_hashed(self):
        user = User.objects.create_user(
            email="student@example.com",
            password="Strong-test-password-123",
        )
        self.assertNotEqual(user.password, "Strong-test-password-123")
        self.assertTrue(user.check_password("Strong-test-password-123"))

    def test_four_system_roles_are_seeded(self):
        expected = {
            RoleCode.ADMINISTRATOR,
            RoleCode.PROJECT_COORDINATOR,
            RoleCode.LECTURER,
            RoleCode.STUDENT,
        }
        actual = set(Role.objects.values_list("code", flat=True))
        self.assertTrue(expected.issubset(actual))

    def test_user_can_have_multiple_global_roles(self):
        user = User.objects.create_user(
            email="lecturer@example.com",
            password="Strong-test-password-123",
        )
        lecturer = Role.objects.get(code=RoleCode.LECTURER)
        coordinator = Role.objects.get(code=RoleCode.PROJECT_COORDINATOR)
        UserRole.objects.create(user=user, role=lecturer)
        UserRole.objects.create(user=user, role=coordinator)
        self.assertTrue(user.has_role(RoleCode.LECTURER))
        self.assertTrue(user.has_role(RoleCode.PROJECT_COORDINATOR))
        self.assertEqual(user.role_assignments.count(), 2)

    def test_superuser_receives_administrator_role(self):
        user = User.objects.create_superuser(
            email="admin@example.com",
            password="Strong-admin-password-123",
        )
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.has_role(RoleCode.ADMINISTRATOR))
