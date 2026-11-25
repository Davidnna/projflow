from importlib import import_module

from django.apps import apps as django_apps
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, connection, transaction
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone
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

    def test_student_and_lecturer_roles_are_mutually_exclusive(self):
        student = User.objects.create_user(
            email="student-role@example.com",
            password="Strong-test-password-123",
        )
        UserRole.objects.create(
            user=student,
            role=Role.objects.get(code=RoleCode.STUDENT),
        )
        with self.assertRaises(DjangoValidationError):
            UserRole.objects.create(
                user=student,
                role=Role.objects.get(code=RoleCode.LECTURER),
            )

        lecturer = User.objects.create_user(
            email="lecturer-role@example.com",
            password="Strong-test-password-123",
        )
        UserRole.objects.create(
            user=lecturer,
            role=Role.objects.get(code=RoleCode.LECTURER),
        )
        with self.assertRaises(DjangoValidationError):
            UserRole.objects.create(
                user=lecturer,
                role=Role.objects.get(code=RoleCode.STUDENT),
            )

    def test_database_rejects_bulk_assignment_of_incompatible_roles(self):
        user = User.objects.create_user(
            email="bulk-role@example.com",
            password="Strong-test-password-123",
        )
        UserRole.objects.create(
            user=user,
            role=Role.objects.get(code=RoleCode.STUDENT),
        )
        lecturer_role = Role.objects.get(code=RoleCode.LECTURER)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                UserRole.objects.bulk_create([
                    UserRole(user=user, role=lecturer_role),
                ])
        self.assertFalse(user.has_role(RoleCode.LECTURER))

    def test_database_rejects_queryset_update_into_incompatible_roles(self):
        student = User.objects.create_user(
            email="student-update@example.com",
            password="Strong-test-password-123",
        )
        lecturer = User.objects.create_user(
            email="lecturer-update@example.com",
            password="Strong-test-password-123",
        )
        student_assignment = UserRole.objects.create(
            user=student,
            role=Role.objects.get(code=RoleCode.STUDENT),
        )
        lecturer_assignment = UserRole.objects.create(
            user=lecturer,
            role=Role.objects.get(code=RoleCode.LECTURER),
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                UserRole.objects.filter(pk=lecturer_assignment.pk).update(
                    user_id=student.pk,
                )
        self.assertTrue(student_assignment.user.has_role(RoleCode.STUDENT))
        self.assertFalse(student.has_role(RoleCode.LECTURER))

    def test_superuser_receives_administrator_role(self):
        user = User.objects.create_superuser(
            email="admin@example.com",
            password="Strong-admin-password-123",
        )
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.has_role(RoleCode.ADMINISTRATOR))


class RoleIntegrityMigrationTests(TransactionTestCase):
    reset_sequences = True

    def test_conflicting_legacy_accounts_are_disabled_without_deleting_student_history(self):
        migration = import_module(
            "apps.accounts.migrations.0003_enforce_student_lecturer_exclusivity"
        )
        with connection.schema_editor() as editor:
            migration.remove_role_triggers(django_apps, editor)

        try:
            student_role = Role.objects.get(code=RoleCode.STUDENT)
            lecturer_role = Role.objects.get(code=RoleCode.LECTURER)
            student_with_both_roles = User.objects.create_user(
                email="legacy-dual-role@example.com",
                password="Strong-test-password-123",
            )
            enrollment_only_student = User.objects.create_user(
                email="legacy-enrollment-only@example.com",
                password="Strong-test-password-123",
            )
            coordinator = User.objects.create_user(
                email="legacy-migration-actor@example.com",
                password="Strong-test-password-123",
            )
            coordinator_role = Role.objects.get(code=RoleCode.PROJECT_COORDINATOR)
            UserRole.objects.bulk_create([
                UserRole(user=student_with_both_roles, role=student_role),
                UserRole(user=student_with_both_roles, role=lecturer_role),
                UserRole(user=enrollment_only_student, role=lecturer_role),
                UserRole(user=coordinator, role=coordinator_role),
            ])

            from apps.academics.models import (
                AcademicSession,
                LecturerProfile,
                StudentEnrollment,
                SupervisorAssignment,
            )
            from apps.projects.models import (
                CompletionEvent,
                DefencePanel,
                ExaminerScore,
                ProjectCompletion,
                ProjectNotification,
            )

            session = AcademicSession.objects.create(name="Legacy role migration session")
            enrollments = StudentEnrollment.objects.bulk_create([
                StudentEnrollment(
                    user=student_with_both_roles,
                    session=session,
                    matric_number="LEGACY/001",
                ),
                StudentEnrollment(
                    user=enrollment_only_student,
                    session=session,
                    matric_number="LEGACY/002",
                ),
            ])
            profiles = LecturerProfile.objects.bulk_create([
                LecturerProfile(user=student_with_both_roles, staff_number="LEGACY-001"),
                LecturerProfile(user=enrollment_only_student, staff_number="LEGACY-002"),
            ])
            valid_examiner = User.objects.create_user(
                email="legacy-valid-examiner@example.com",
                password="Strong-test-password-123",
            )
            valid_examiner_profile = LecturerProfile.objects.create(user=valid_examiner)
            UserRole.objects.create(
                user=valid_examiner,
                role=lecturer_role,
            )
            assignments = [
                SupervisorAssignment.objects.create(
                    student_enrollment=enrollment,
                    lecturer=profile,
                    assigned_by=coordinator,
                )
                for enrollment, profile in zip(enrollments, profiles)
            ]
            panel = DefencePanel.objects.create(
                session=session,
                name="Legacy dual-role panel",
                created_by=coordinator,
            )
            panel.members.set([profiles[0], valid_examiner_profile])
            published_at = timezone.now()
            project = ProjectCompletion.objects.create(
                enrollment=enrollments[0],
                status="published",
                panel=panel,
                defence_at=published_at,
                venue="Legacy hall",
                components=[{"name": "Report", "maximum": 60}, {"name": "Defence", "maximum": 40}],
                score_round=1,
                published_result={"overall": "80.00"},
                published_at=published_at,
            )
            ExaminerScore.objects.create(
                project=project,
                examiner=profiles[0],
                round=1,
                marks=["50.00", "30.00"],
            )
            ExaminerScore.objects.create(
                project=project,
                examiner=valid_examiner_profile,
                round=1,
                marks=["55.00", "35.00"],
            )

            with connection.schema_editor() as editor:
                migration.clean_conflicting_accounts(django_apps, editor)

            student_with_both_roles.refresh_from_db()
            enrollment_only_student.refresh_from_db()
            self.assertTrue(student_with_both_roles.has_role(RoleCode.STUDENT))
            self.assertFalse(student_with_both_roles.has_role(RoleCode.LECTURER))
            self.assertTrue(enrollment_only_student.has_role(RoleCode.STUDENT))
            self.assertFalse(enrollment_only_student.has_role(RoleCode.LECTURER))
            self.assertEqual(StudentEnrollment.objects.filter(pk__in=[e.pk for e in enrollments]).count(), 2)
            self.assertEqual(LecturerProfile.objects.filter(pk__in=[p.pk for p in profiles]).count(), 2)
            self.assertFalse(LecturerProfile.objects.filter(pk__in=[p.pk for p in profiles], is_active=True).exists())
            self.assertEqual(SupervisorAssignment.objects.filter(pk__in=[a.pk for a in assignments]).count(), 2)
            for assignment in assignments:
                assignment.refresh_from_db()
                self.assertFalse(assignment.is_current)
                self.assertIsNotNone(assignment.ended_at)
                self.assertIn("role-integrity migration", assignment.reassignment_reason)
            project.refresh_from_db()
            self.assertEqual(project.status, "panel_reallocation_required")
            self.assertIsNone(project.panel_id)
            self.assertEqual(project.score_round, 2)
            self.assertEqual(project.published_result, {})
            self.assertIsNone(project.published_at)
            self.assertEqual(project.scores.count(), 2)
            self.assertEqual(project.scores.values_list("round", flat=True).distinct().get(), 1)
            self.assertEqual(panel.members.count(), 1)
            event = CompletionEvent.objects.get(project=project, action="panel_reallocation_required")
            self.assertEqual(event.data["previous_published_result"], {"overall": "80.00"})
            self.assertEqual(event.data["previous_panel_id"], str(panel.pk))
            self.assertTrue(ProjectNotification.objects.filter(recipient=student_with_both_roles, category="defence").exists())
            self.assertTrue(ProjectNotification.objects.filter(recipient=coordinator, category="defence").exists())
            self.assertTrue(ProjectNotification.objects.filter(recipient=student_with_both_roles, category="supervision").exists())
            self.assertTrue(ProjectNotification.objects.filter(recipient=coordinator, category="supervision").exists())
        finally:
            with connection.schema_editor() as editor:
                migration.install_role_triggers(django_apps, editor)


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


class CoordinatorAccessTests(APITestCase):
    def setUp(self):
        self.administrator = User.objects.create_superuser(
            email="admin-coordinator@example.com",
            password="Strong-admin-password-123",
        )
        self.lecturer = User.objects.create_user(
            email="lecturer-coordinator@example.com",
            password="Strong-lecturer-password-123",
            first_name="Ada",
            last_name="Lecturer",
        )
        UserRole.objects.create(
            user=self.lecturer,
            role=Role.objects.get(code=RoleCode.LECTURER),
        )
        self.student = User.objects.create_user(
            email="student-coordinator@example.com",
            password="Strong-student-password-123",
        )
        UserRole.objects.create(
            user=self.student,
            role=Role.objects.get(code=RoleCode.STUDENT),
        )
        self.endpoint = "/api/auth/coordinator-access/"

    def test_administrator_can_list_eligible_staff_accounts(self):
        self.client.force_authenticate(self.administrator)
        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        account_ids = {item["id"] for item in response.data}
        self.assertIn(str(self.administrator.pk), account_ids)
        self.assertIn(str(self.lecturer.pk), account_ids)
        self.assertNotIn(str(self.student.pk), account_ids)

    def test_administrator_can_grant_coordinator_access_to_self(self):
        self.client.force_authenticate(self.administrator)
        response = self.client.post(
            self.endpoint,
            {"user_id": str(self.administrator.pk), "enabled": True},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(self.administrator.has_role(RoleCode.PROJECT_COORDINATOR))
        self.assertTrue(response.data["account"]["has_coordinator_access"])

    def test_administrator_can_grant_coordinator_access_to_lecturer(self):
        self.client.force_authenticate(self.administrator)
        response = self.client.post(
            self.endpoint,
            {"user_id": str(self.lecturer.pk), "enabled": True},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(self.lecturer.has_role(RoleCode.PROJECT_COORDINATOR))

    def test_administrator_can_revoke_coordinator_access(self):
        coordinator_role = Role.objects.get(code=RoleCode.PROJECT_COORDINATOR)
        UserRole.objects.create(user=self.lecturer, role=coordinator_role)
        self.client.force_authenticate(self.administrator)
        response = self.client.post(
            self.endpoint,
            {"user_id": str(self.lecturer.pk), "enabled": False},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(self.lecturer.has_role(RoleCode.PROJECT_COORDINATOR))

    def test_non_administrator_cannot_manage_coordinator_access(self):
        self.client.force_authenticate(self.lecturer)
        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_student_cannot_receive_coordinator_access(self):
        self.client.force_authenticate(self.administrator)
        response = self.client.post(
            self.endpoint,
            {"user_id": str(self.student.pk), "enabled": True},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(self.student.has_role(RoleCode.PROJECT_COORDINATOR))
