from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.test import APITestCase
from openpyxl import Workbook

from apps.accounts.models import Role, RoleCode, UserRole

from .models import (
    AcademicSession,
    AcademicSessionStatus,
    LecturerProfile,
    RosterRecordSource,
    StudentEnrollment,
    StudentRosterRecord,
    StudentVerificationStatus,
    SupervisorAssignment,
)
from .services import activate_academic_session

User = get_user_model()


class AcademicTestDataMixin:
    def create_user_with_role(self, email, role_code, password="Strong-test-password-123"):
        user = User.objects.create_user(
            email=email,
            password=password,
            first_name="Test",
            last_name="User",
        )
        role = Role.objects.get(code=role_code)
        UserRole.objects.create(user=user, role=role)
        return user

    def create_active_session(self, actor=None, name="2026/2027"):
        session = AcademicSession.objects.create(
            name=name,
            created_by=actor,
        )
        if actor:
            activate_academic_session(session.pk, actor)
            session.refresh_from_db()
        else:
            session.status = AcademicSessionStatus.ACTIVE
            session.save(update_fields=["status"])
        return session


class AcademicSessionAPITests(AcademicTestDataMixin, APITestCase):
    def setUp(self):
        self.coordinator = self.create_user_with_role(
            "coordinator@example.com",
            RoleCode.PROJECT_COORDINATOR,
        )
        self.client.force_authenticate(self.coordinator)

    def test_coordinator_creates_and_activates_session(self):
        response = self.client.post(
            "/api/academics/sessions/",
            {
                "name": "2026/2027",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], AcademicSessionStatus.PLANNED)
        self.assertNotIn("start_date", response.data)
        self.assertNotIn("end_date", response.data)
        created_session = AcademicSession.objects.get(pk=response.data["id"])
        self.assertIsNone(created_session.start_date)
        self.assertIsNone(created_session.end_date)

        activation = self.client.post(
            f"/api/academics/sessions/{response.data['id']}/activate/",
            {},
            format="json",
        )
        self.assertEqual(activation.status_code, status.HTTP_200_OK)
        self.assertEqual(activation.data["status"], AcademicSessionStatus.ACTIVE)

    def test_second_session_cannot_be_activated_until_first_is_closed(self):
        first = self.create_active_session(self.coordinator)
        second = AcademicSession.objects.create(name="2027/2028")
        response = self.client.post(
            f"/api/academics/sessions/{second.pk}/activate/",
            {},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        first.refresh_from_db()
        self.assertEqual(first.status, AcademicSessionStatus.ACTIVE)

        close_response = self.client.post(
            f"/api/academics/sessions/{first.pk}/close/",
            {},
            format="json",
        )
        self.assertEqual(close_response.status_code, status.HTTP_200_OK)
        activate_response = self.client.post(
            f"/api/academics/sessions/{second.pk}/activate/",
            {},
            format="json",
        )
        self.assertEqual(activate_response.status_code, status.HTTP_200_OK)

    def test_lecturer_cannot_create_academic_session(self):
        lecturer = self.create_user_with_role("lecturer@example.com", RoleCode.LECTURER)
        self.client.force_authenticate(lecturer)
        response = self.client.post(
            "/api/academics/sessions/",
            {
                "name": "2026/2027",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class StudentRosterAPITests(AcademicTestDataMixin, APITestCase):
    def setUp(self):
        self.coordinator = self.create_user_with_role(
            "coordinator@example.com",
            RoleCode.PROJECT_COORDINATOR,
        )
        self.session = AcademicSession.objects.create(name="2026/2027")
        self.client.force_authenticate(self.coordinator)

    def test_coordinator_can_add_student_roster_record(self):
        response = self.client.post(
            "/api/academics/roster/",
            {
                "session": str(self.session.pk),
                "matric_number": " cs/2026/001 ",
                "first_name": "Ada",
                "last_name": "Okafor",
                "other_names": "Chiamaka",
                "is_eligible": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["matric_number"], "CS/2026/001")
        self.assertEqual(response.data["source"], RosterRecordSource.MANUAL)

    def test_duplicate_matric_number_is_rejected_within_session(self):
        StudentRosterRecord.objects.create(
            session=self.session,
            matric_number="CS/2026/001",
            first_name="Ada",
            last_name="Okafor",
        )
        response = self.client.post(
            "/api/academics/roster/",
            {
                "session": str(self.session.pk),
                "matric_number": "cs/2026/001",
                "first_name": "Another",
                "last_name": "Student",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_student_cannot_manage_roster(self):
        student = self.create_user_with_role("student@example.com", RoleCode.STUDENT)
        self.client.force_authenticate(student)
        response = self.client.get("/api/academics/roster/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_xlsx_import_preview(self):
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.append(["matric_number", "first_name", "last_name", "email"])
        worksheet.append(["CS/2026/010", "Ngozi", "Eze", "ngozi@example.com"])
        content = BytesIO()
        workbook.save(content)
        upload = SimpleUploadedFile(
            "students.xlsx",
            content.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response = self.client.post(
            "/api/academics/roster-imports/preview/",
            {"session": str(self.session.pk), "file": upload},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["valid_rows"], 1)
        self.assertEqual(response.data["rows"][0]["matric_number"], "CS/2026/010")

    def test_csv_import_preview_and_commit(self):
        csv_content = (
            "matric_number,first_name,last_name,email,is_eligible\n"
            "CS/2026/001,Ada,Okafor,ada@example.com,yes\n"
            "CS/2026/001,Duplicate,Student,,yes\n"
            ",Missing,Matric,,yes\n"
        )
        upload = SimpleUploadedFile(
            "students.csv",
            csv_content.encode("utf-8"),
            content_type="text/csv",
        )
        preview = self.client.post(
            "/api/academics/roster-imports/preview/",
            {"session": str(self.session.pk), "file": upload},
            format="multipart",
        )
        self.assertEqual(preview.status_code, status.HTTP_201_CREATED)
        self.assertEqual(preview.data["valid_rows"], 1)
        self.assertEqual(preview.data["duplicate_rows"], 1)
        self.assertEqual(preview.data["invalid_rows"], 1)

        commit = self.client.post(
            f"/api/academics/roster-imports/{preview.data['id']}/commit/",
            {},
            format="json",
        )
        self.assertEqual(commit.status_code, status.HTTP_200_OK)
        self.assertEqual(commit.data["imported_rows"], 1)
        self.assertEqual(
            StudentRosterRecord.objects.filter(session=self.session).count(),
            1,
        )


class StudentRegistrationAPITests(AcademicTestDataMixin, APITestCase):
    def setUp(self):
        self.coordinator = self.create_user_with_role(
            "coordinator@example.com",
            RoleCode.PROJECT_COORDINATOR,
        )
        self.session = self.create_active_session(self.coordinator)

    def registration_payload(self, **overrides):
        payload = {
            "email": "ada@example.com",
            "password": "Unique-Student-Password-927!",
            "first_name": "Ada",
            "last_name": "Okafor",
            "other_names": "Chiamaka",
            "matric_number": "CS/2026/001",
            "phone": "",
        }
        payload.update(overrides)
        return payload

    def test_matching_roster_record_is_automatically_verified(self):
        StudentRosterRecord.objects.create(
            session=self.session,
            matric_number="CS/2026/001",
            first_name="Ada",
            last_name="Okafor",
            other_names="Chiamaka",
        )
        response = self.client.post(
            "/api/auth/register/",
            self.registration_payload(),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data["enrollment"]["verification_status"],
            StudentVerificationStatus.AUTO_VERIFIED,
        )
        user = User.objects.get(email="ada@example.com")
        self.assertTrue(user.has_role(RoleCode.STUDENT))

    def test_all_populated_roster_details_are_matched_for_automatic_verification(self):
        StudentRosterRecord.objects.create(
            session=self.session,
            matric_number="CS/2026/001",
            first_name="Ada",
            last_name="Okafor",
            other_names="Chiamaka",
            email="ADA@EXAMPLE.COM",
            phone="0803 000-0001",
        )
        response = self.client.post(
            "/api/auth/register/",
            self.registration_payload(phone="08030000001"),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data["enrollment"]["verification_status"],
            StudentVerificationStatus.AUTO_VERIFIED,
        )
        enrollment = StudentEnrollment.objects.get(user__email="ada@example.com")
        self.assertEqual(enrollment.verification_notes, "")
        self.assertEqual(enrollment.phone, "08030000001")
        self.assertNotIn("verification_notes", response.data["enrollment"])
        self.assertNotIn("verification_method", response.data["enrollment"])
        self.assertNotIn("user_id", response.data)

    def test_missing_roster_record_is_referred_with_a_clear_reason(self):
        response = self.client.post(
            "/api/auth/register/",
            self.registration_payload(),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data["enrollment"]["verification_status"],
            StudentVerificationStatus.PENDING_REVIEW,
        )
        enrollment = StudentEnrollment.objects.get(user__email="ada@example.com")
        self.assertIn("No matching matriculation number", enrollment.verification_notes)
        self.assertNotIn("verification_notes", response.data["enrollment"])

    def test_ineligible_roster_record_is_referred_for_manual_review(self):
        StudentRosterRecord.objects.create(
            session=self.session,
            matric_number="CS/2026/001",
            first_name="Ada",
            last_name="Okafor",
            other_names="Chiamaka",
            is_eligible=False,
        )
        response = self.client.post(
            "/api/auth/register/",
            self.registration_payload(),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data["enrollment"]["verification_status"],
            StudentVerificationStatus.PENDING_REVIEW,
        )
        enrollment = StudentEnrollment.objects.get(user__email="ada@example.com")
        self.assertIn("not marked as eligible", enrollment.verification_notes)

    def test_email_mismatch_is_referred_for_manual_review(self):
        StudentRosterRecord.objects.create(
            session=self.session,
            matric_number="CS/2026/001",
            first_name="Ada",
            last_name="Okafor",
            other_names="Chiamaka",
            email="departmental@example.com",
        )
        response = self.client.post(
            "/api/auth/register/",
            self.registration_payload(),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data["enrollment"]["verification_status"],
            StudentVerificationStatus.PENDING_REVIEW,
        )
        enrollment = StudentEnrollment.objects.get(user__email="ada@example.com")
        self.assertIn("Email address does not match", enrollment.verification_notes)

    def test_phone_mismatch_is_referred_for_manual_review(self):
        StudentRosterRecord.objects.create(
            session=self.session,
            matric_number="CS/2026/001",
            first_name="Ada",
            last_name="Okafor",
            other_names="Chiamaka",
            phone="08030000001",
        )
        response = self.client.post(
            "/api/auth/register/",
            self.registration_payload(phone="08030000002"),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data["enrollment"]["verification_status"],
            StudentVerificationStatus.PENDING_REVIEW,
        )
        enrollment = StudentEnrollment.objects.get(user__email="ada@example.com")
        self.assertIn("Phone number does not match", enrollment.verification_notes)

    def test_missing_recorded_other_names_are_referred_for_manual_review(self):
        StudentRosterRecord.objects.create(
            session=self.session,
            matric_number="CS/2026/001",
            first_name="Ada",
            last_name="Okafor",
            other_names="Chiamaka",
        )
        response = self.client.post(
            "/api/auth/register/",
            self.registration_payload(other_names=""),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data["enrollment"]["verification_status"],
            StudentVerificationStatus.PENDING_REVIEW,
        )
        enrollment = StudentEnrollment.objects.get(user__email="ada@example.com")
        self.assertIn("Other names do not match", enrollment.verification_notes)

    def test_name_mismatch_is_referred_for_manual_review(self):
        StudentRosterRecord.objects.create(
            session=self.session,
            matric_number="CS/2026/001",
            first_name="Ada",
            last_name="Okafor",
        )
        response = self.client.post(
            "/api/auth/register/",
            self.registration_payload(first_name="Different"),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data["enrollment"]["verification_status"],
            StudentVerificationStatus.PENDING_REVIEW,
        )

    def test_registration_requires_active_academic_session(self):
        self.session.status = AcademicSessionStatus.CLOSED
        self.session.save(update_fields=["status"])
        response = self.client.post(
            "/api/auth/register/",
            self.registration_payload(),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_student_status_endpoints_do_not_expose_internal_verification_details(self):
        registration = self.client.post(
            "/api/auth/register/",
            self.registration_payload(first_name="Unmatched"),
            format="json",
        )
        self.assertEqual(registration.status_code, status.HTTP_201_CREATED)
        student_user = User.objects.get(email="ada@example.com")
        self.client.force_authenticate(student_user)

        for url in [
            "/api/academics/enrollments/mine/",
            "/api/academics/enrollments/",
        ]:
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            if isinstance(response.data, list):
                records = response.data
            elif isinstance(response.data, dict) and isinstance(response.data.get("results"), list):
                records = response.data["results"]
            else:
                records = [response.data]
            for record in records:
                self.assertNotIn("verification_notes", record)
                self.assertNotIn("verification_method", record)
                self.assertNotIn("review_notes", record)
                self.assertNotIn("reviewed_by", record)
                self.assertNotIn("verified_at", record)

    def test_coordinator_can_manually_approve_pending_registration(self):
        registration = self.client.post(
            "/api/auth/register/",
            self.registration_payload(first_name="Unmatched"),
            format="json",
        )
        self.assertEqual(registration.status_code, status.HTTP_201_CREATED)
        student_user = User.objects.get(email="ada@example.com")
        enrollment_id = StudentEnrollment.objects.get(
            user=student_user,
            session=self.session,
        ).pk
        self.client.force_authenticate(self.coordinator)
        review = self.client.post(
            f"/api/academics/enrollments/{enrollment_id}/review/",
            {"decision": "approve", "notes": "Verified against departmental records."},
            format="json",
        )
        self.assertEqual(review.status_code, status.HTTP_200_OK)
        self.assertEqual(
            review.data["verification_status"],
            StudentVerificationStatus.MANUALLY_APPROVED,
        )


class StudentLecturerBoundaryTests(AcademicTestDataMixin, APITestCase):
    def setUp(self):
        self.session = AcademicSession.objects.create(name="Role boundary session")

    def test_student_cannot_receive_a_lecturer_profile(self):
        student = self.create_user_with_role("student-profile@example.com", RoleCode.STUDENT)
        with self.assertRaises(DjangoValidationError):
            LecturerProfile.objects.create(user=student)

    def test_lecturer_cannot_be_enrolled_as_a_student(self):
        lecturer = self.create_user_with_role("lecturer-enrollment@example.com", RoleCode.LECTURER)
        with self.assertRaises(DjangoValidationError):
            StudentEnrollment.objects.create(
                user=lecturer,
                session=self.session,
                matric_number="ROLE/001",
            )

    def test_active_lecturer_profile_cannot_be_enrolled_without_a_lecturer_role(self):
        profile_only_user = User.objects.create_user(
            email="profile-only-enrollment@example.com",
            password="Strong-test-password-123",
        )
        LecturerProfile.objects.create(user=profile_only_user, staff_number="PROFILE-001")
        with self.assertRaises(DjangoValidationError):
            StudentEnrollment.objects.create(
                user=profile_only_user,
                session=self.session,
                matric_number="ROLE/004",
            )

    def test_database_rejects_bulk_student_enrollment_for_lecturer(self):
        lecturer = self.create_user_with_role("lecturer-bulk-enrollment@example.com", RoleCode.LECTURER)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                StudentEnrollment.objects.bulk_create([
                    StudentEnrollment(
                        user=lecturer,
                        session=self.session,
                        matric_number="ROLE/002",
                    ),
                ])
        self.assertFalse(StudentEnrollment.objects.filter(user=lecturer).exists())

    def test_database_rejects_bulk_lecturer_profile_for_student(self):
        student = self.create_user_with_role("student-bulk-profile@example.com", RoleCode.STUDENT)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                LecturerProfile.objects.bulk_create([
                    LecturerProfile(user=student, staff_number="ROLE-STAFF-001"),
                ])
        self.assertFalse(LecturerProfile.objects.filter(user=student).exists())

    def test_student_enrollment_prevents_later_lecturer_role_assignment(self):
        enrolled_user = User.objects.create_user(
            email="enrolled-without-role@example.com",
            password="Strong-test-password-123",
        )
        StudentEnrollment.objects.create(
            user=enrolled_user,
            session=self.session,
            matric_number="ROLE/003",
        )
        with self.assertRaises(DjangoValidationError):
            LecturerProfile.objects.create(user=enrolled_user)
        with self.assertRaises(DjangoValidationError):
            UserRole.objects.create(
                user=enrolled_user,
                role=Role.objects.get(code=RoleCode.LECTURER),
            )
        lecturer_role = Role.objects.get(code=RoleCode.LECTURER)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                UserRole.objects.bulk_create([
                    UserRole(user=enrolled_user, role=lecturer_role),
                ])

    def test_inactive_lecturer_profile_cannot_be_reactivated_after_student_role_assignment(self):
        former_lecturer = User.objects.create_user(
            email="former-lecturer@example.com",
            password="Strong-test-password-123",
        )
        profile = LecturerProfile.objects.create(
            user=former_lecturer,
            staff_number="FORMER-001",
            is_active=False,
        )
        UserRole.objects.create(
            user=former_lecturer,
            role=Role.objects.get(code=RoleCode.STUDENT),
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                LecturerProfile.objects.filter(pk=profile.pk).update(is_active=True)
        profile.refresh_from_db()
        self.assertFalse(profile.is_active)

    def test_active_lecturer_profile_blocks_student_role_assignment(self):
        lecturer_profile_user = User.objects.create_user(
            email="active-profile-user@example.com",
            password="Strong-test-password-123",
        )
        LecturerProfile.objects.create(
            user=lecturer_profile_user,
            staff_number="ACTIVE-001",
        )
        student_role = Role.objects.get(code=RoleCode.STUDENT)
        with self.assertRaises(DjangoValidationError):
            UserRole.objects.create(user=lecturer_profile_user, role=student_role)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                UserRole.objects.bulk_create([
                    UserRole(user=lecturer_profile_user, role=student_role),
                ])


class LecturerAndSupervisorAPITests(AcademicTestDataMixin, APITestCase):
    def setUp(self):
        self.coordinator = self.create_user_with_role(
            "coordinator@example.com",
            RoleCode.PROJECT_COORDINATOR,
        )
        self.session = self.create_active_session(self.coordinator)
        self.student = User.objects.create_user(
            email="student@example.com",
            password="Strong-student-password-123",
            first_name="Ada",
            last_name="Okafor",
        )
        UserRole.objects.create(
            user=self.student,
            role=Role.objects.get(code=RoleCode.STUDENT),
        )
        self.enrollment = StudentEnrollment.objects.create(
            user=self.student,
            session=self.session,
            matric_number="CS/2026/001",
            verification_status=StudentVerificationStatus.AUTO_VERIFIED,
            verification_method="automatic",
        )
        self.lecturer_one = self.create_lecturer("lecturer.one@example.com", "STAFF001")
        self.lecturer_two = self.create_lecturer("lecturer.two@example.com", "STAFF002")
        self.client.force_authenticate(self.coordinator)

    def create_lecturer(self, email, staff_number):
        user = self.create_user_with_role(email, RoleCode.LECTURER)
        return LecturerProfile.objects.create(user=user, staff_number=staff_number)

    def test_coordinator_can_create_lecturer_account(self):
        response = self.client.post(
            "/api/academics/lecturers/",
            {
                "email": "new.lecturer@example.com",
                "password": "Strong-Lecturer-Password-927!",
                "first_name": "Grace",
                "last_name": "Nwosu",
                "staff_number": "STAFF003",
                "designation": "Lecturer II",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.get(email="new.lecturer@example.com").has_role(RoleCode.LECTURER))

    def test_coordinator_can_assign_and_reassign_supervisor(self):
        assignment_response = self.client.post(
            "/api/academics/supervisor-assignments/assign/",
            {
                "student_enrollment": str(self.enrollment.pk),
                "lecturer": str(self.lecturer_one.pk),
            },
            format="json",
        )
        self.assertEqual(assignment_response.status_code, status.HTTP_201_CREATED)

        missing_reason = self.client.post(
            f"/api/academics/supervisor-assignments/{assignment_response.data['id']}/reassign/",
            {"lecturer": str(self.lecturer_two.pk), "reason": " "},
            format="json",
        )
        self.assertEqual(missing_reason.status_code, status.HTTP_400_BAD_REQUEST)

        reassignment = self.client.post(
            f"/api/academics/supervisor-assignments/{assignment_response.data['id']}/reassign/",
            {
                "lecturer": str(self.lecturer_two.pk),
                "reason": "Departmental workload adjustment.",
            },
            format="json",
        )
        self.assertEqual(reassignment.status_code, status.HTTP_201_CREATED)
        self.assertEqual(SupervisorAssignment.objects.filter(student_enrollment=self.enrollment).count(), 2)
        old_assignment = SupervisorAssignment.objects.get(pk=assignment_response.data["id"])
        self.assertFalse(old_assignment.is_current)
        self.assertEqual(old_assignment.ended_by, self.coordinator)
        self.assertEqual(reassignment.data["reassignment_reason"], "Departmental workload adjustment.")

    def test_unverified_student_cannot_be_assigned_a_supervisor(self):
        self.enrollment.verification_status = StudentVerificationStatus.PENDING_REVIEW
        self.enrollment.save(update_fields=["verification_status"])
        response = self.client.post(
            "/api/academics/supervisor-assignments/assign/",
            {
                "student_enrollment": str(self.enrollment.pk),
                "lecturer": str(self.lecturer_one.pk),
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(SupervisorAssignment.objects.filter(student_enrollment=self.enrollment).count(), 0)

    def test_student_cannot_assign_a_supervisor(self):
        self.client.force_authenticate(self.student)
        response = self.client.post(
            "/api/academics/supervisor-assignments/assign/",
            {
                "student_enrollment": str(self.enrollment.pk),
                "lecturer": str(self.lecturer_one.pk),
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_workload_endpoint_orders_lecturers_by_active_supervisees(self):
        assign_response = self.client.post(
            "/api/academics/supervisor-assignments/assign/",
            {
                "student_enrollment": str(self.enrollment.pk),
                "lecturer": str(self.lecturer_one.pk),
            },
            format="json",
        )
        self.assertEqual(assign_response.status_code, status.HTTP_201_CREATED)
        response = self.client.get("/api/academics/lecturer-workloads/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["lecturer_id"], str(self.lecturer_two.pk))
        self.assertEqual(response.data[0]["active_supervisee_count"], 0)


class AuthenticationAPITests(AcademicTestDataMixin, APITestCase):
    def test_user_can_obtain_jwt_pair(self):
        user = User.objects.create_user(
            email="login@example.com",
            password="Strong-login-password-123",
        )
        response = self.client.post(
            "/api/auth/token/",
            {"email": user.email, "password": "Strong-login-password-123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["user"]["email"], user.email)

    def test_logout_blacklists_refresh_token(self):
        user = User.objects.create_user(
            email="logout@example.com",
            password="Strong-logout-password-123",
        )
        token_response = self.client.post(
            "/api/auth/token/",
            {"email": user.email, "password": "Strong-logout-password-123"},
            format="json",
        )
        self.assertEqual(token_response.status_code, status.HTTP_200_OK)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {token_response.data['access']}"
        )
        logout_response = self.client.post(
            "/api/auth/logout/",
            {"refresh": token_response.data["refresh"]},
            format="json",
        )
        self.assertEqual(logout_response.status_code, status.HTTP_205_RESET_CONTENT)
        refresh_response = self.client.post(
            "/api/auth/token/refresh/",
            {"refresh": token_response.data["refresh"]},
            format="json",
        )
        self.assertEqual(refresh_response.status_code, status.HTTP_401_UNAUTHORIZED)
