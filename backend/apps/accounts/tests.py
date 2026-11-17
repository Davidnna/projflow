from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APITestCase

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


class InitialAdministratorSetupTests(APITestCase):
    setup_token = "projflow-initial-setup-secret-48-characters-long"
    endpoint = "/api/auth/initial-admin/"

    def setUp(self):
        cache.clear()

    @override_settings(PROJFLOW_INITIAL_ADMIN_SETUP_TOKEN="")
    def test_setup_is_unavailable_without_configured_secret(self):
        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["setup_available"])

    @override_settings(PROJFLOW_INITIAL_ADMIN_SETUP_TOKEN=setup_token)
    def test_setup_is_available_before_first_administrator(self):
        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["setup_available"])

    @override_settings(PROJFLOW_INITIAL_ADMIN_SETUP_TOKEN=setup_token)
    def test_invalid_setup_secret_is_rejected(self):
        response = self.client.post(
            self.endpoint,
            {
                "setup_token": "incorrect-secret",
                "email": "admin@example.com",
                "first_name": "System",
                "last_name": "Administrator",
                "password": "R7!vQ2#pL9@zN4$wX6",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(User.objects.filter(is_superuser=True).exists())

    @override_settings(PROJFLOW_INITIAL_ADMIN_SETUP_TOKEN=setup_token)
    def test_valid_setup_creates_first_administrator_and_role(self):
        response = self.client.post(
            self.endpoint,
            {
                "setup_token": self.setup_token,
                "email": "Admin@Example.com",
                "first_name": "System",
                "last_name": "Administrator",
                "password": "R7!vQ2#pL9@zN4$wX6",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email="admin@example.com")
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.has_role(RoleCode.ADMINISTRATOR))
        self.assertTrue(user.check_password("R7!vQ2#pL9@zN4$wX6"))

    @override_settings(PROJFLOW_INITIAL_ADMIN_SETUP_TOKEN=setup_token)
    def test_setup_cannot_create_a_second_administrator(self):
        User.objects.create_superuser(
            email="existing-admin@example.com",
            password="R7!vQ2#pL9@zN4$wX6",
        )
        response = self.client.post(
            self.endpoint,
            {
                "setup_token": self.setup_token,
                "email": "second-admin@example.com",
                "first_name": "Second",
                "last_name": "Administrator",
                "password": "R7!vQ2#pL9@zN4$wX6",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_410_GONE)
        self.assertEqual(User.objects.filter(is_superuser=True).count(), 1)
        availability_response = self.client.get(self.endpoint)
        self.assertFalse(availability_response.data["setup_available"])
