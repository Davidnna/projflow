from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Role, RoleCode, UserRole
from apps.academics.services import reassign_supervisor
from apps.academics.models import (
    AcademicSession,
    AcademicSessionStatus,
    LecturerProfile,
    StudentEnrollment,
    StudentVerificationStatus,
    SupervisorAssignment,
    VerificationMethod,
)

from .models import ProjectTopic, ProjectTopicDecision, ProjectTopicRevision, ProjectTopicStatus

User = get_user_model()


class ProjectTopicAPITests(APITestCase):
    def setUp(self):
        self.student = self.create_user("student@example.com", RoleCode.STUDENT)
        self.lecturer = self.create_user("supervisor@example.com", RoleCode.LECTURER)
        self.other_lecturer = self.create_user("other.supervisor@example.com", RoleCode.LECTURER)
        self.coordinator = self.create_user("coordinator@example.com", RoleCode.PROJECT_COORDINATOR)
        self.session = AcademicSession.objects.create(
            name="2026/2027",
            status=AcademicSessionStatus.ACTIVE,
        )
        self.enrollment = StudentEnrollment.objects.create(
            user=self.student,
            session=self.session,
            matric_number="CS/2026/001",
            verification_status=StudentVerificationStatus.AUTO_VERIFIED,
            verification_method=VerificationMethod.AUTOMATIC,
        )
        self.lecturer_profile = LecturerProfile.objects.create(user=self.lecturer)
        self.other_lecturer_profile = LecturerProfile.objects.create(user=self.other_lecturer)
        self.assignment = SupervisorAssignment.objects.create(
            student_enrollment=self.enrollment,
            lecturer=self.lecturer_profile,
            assigned_by=self.coordinator,
        )
        self.valid_payload = {
            "title": "A Web-Based Inventory Management System for Small Retail Businesses",
            "abstract": (
                "This project proposes the design and implementation of a web-based inventory "
                "management system for small retail businesses. The system will support stock "
                "tracking, product records and inventory reporting."
            ),
            "problem_statement": (
                "Small retail businesses often rely on manual stock records, which can cause "
                "inaccurate inventory counts, delayed reporting and avoidable stock shortages."
            ),
            "research_objectives": (
                "The study aims to analyse existing inventory practices, design a web-based "
                "inventory system, implement its core functions and evaluate its usability."
            ),
            "keywords": ["inventory management", "web application", "retail", "stock control"],
        }

    def create_user(self, email, role_code):
        user = User.objects.create_user(
            email=email,
            password="Strong-test-password-123",
            first_name="Test",
            last_name="User",
        )
        role = Role.objects.get(code=role_code)
        UserRole.objects.create(user=user, role=role)
        return user

    def test_student_can_submit_topic_when_verified_and_assigned(self):
        self.client.force_authenticate(self.student)
        response = self.client.post("/api/projects/topics/", self.valid_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        topic = ProjectTopic.objects.get(pk=response.data["id"])
        self.assertEqual(topic.status, ProjectTopicStatus.SUBMITTED)
        self.assertEqual(topic.supervisor_assignment_id, self.assignment.pk)
        self.assertEqual(topic.revisions.count(), 1)
        self.assertEqual(response.data["supervisor_name"], "Test User")

    def test_student_cannot_submit_without_current_supervisor(self):
        self.assignment.is_current = False
        self.assignment.save(update_fields=["is_current"])
        self.client.force_authenticate(self.student)
        response = self.client.post("/api/projects/topics/", self.valid_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("supervisor", str(response.data).lower())

    def test_unverified_student_cannot_submit_topic(self):
        self.enrollment.verification_status = StudentVerificationStatus.PENDING_REVIEW
        self.enrollment.save(update_fields=["verification_status"])
        self.client.force_authenticate(self.student)
        response = self.client.post("/api/projects/topics/", self.valid_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_assigned_supervisor_can_request_revision_and_student_can_resubmit(self):
        topic = self.create_topic()
        self.client.force_authenticate(self.lecturer)
        review = self.client.post(
            f"/api/projects/topics/{topic.pk}/review/",
            {"decision": ProjectTopicDecision.REQUEST_REVISION, "feedback": "Clarify the research scope and target users."},
            format="json",
        )
        self.assertEqual(review.status_code, status.HTTP_200_OK)
        topic.refresh_from_db()
        self.assertEqual(topic.status, ProjectTopicStatus.REVISION_REQUESTED)

        self.client.force_authenticate(self.student)
        revised_payload = {**self.valid_payload, "title": "A Web-Based Inventory Management System for Independent Retail Stores"}
        resubmit = self.client.post(
            f"/api/projects/topics/{topic.pk}/resubmit/",
            revised_payload,
            format="json",
        )
        self.assertEqual(resubmit.status_code, status.HTTP_200_OK)
        topic.refresh_from_db()
        self.assertEqual(topic.status, ProjectTopicStatus.SUBMITTED)
        self.assertEqual(topic.revisions.count(), 2)
        self.assertEqual(topic.title, revised_payload["title"])

    def test_only_assigned_supervisor_can_review_topic(self):
        topic = self.create_topic()
        self.client.force_authenticate(self.other_lecturer)
        response = self.client.post(
            f"/api/projects/topics/{topic.pk}/review/",
            {"decision": ProjectTopicDecision.APPROVE, "feedback": "Approved."},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_assigned_supervisor_can_approve_topic(self):
        topic = self.create_topic()
        self.client.force_authenticate(self.lecturer)
        response = self.client.post(
            f"/api/projects/topics/{topic.pk}/review/",
            {"decision": ProjectTopicDecision.APPROVE, "feedback": "The proposal is approved."},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        topic.refresh_from_db()
        self.assertEqual(topic.status, ProjectTopicStatus.APPROVED)
        self.assertTrue(topic.is_current)

    def test_supervisor_review_queue_only_returns_assigned_submissions(self):
        topic = self.create_topic()
        self.client.force_authenticate(self.other_lecturer)
        response = self.client.get("/api/projects/topics/review-queue/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])
        self.client.force_authenticate(self.lecturer)
        response = self.client.get("/api/projects/topics/review-queue/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item["id"] for item in response.data], [str(topic.pk)])

    def test_supervisor_can_view_topics_they_have_approved(self):
        topic = self.create_topic()
        self.client.force_authenticate(self.lecturer)
        review = self.client.post(
            f"/api/projects/topics/{topic.pk}/review/",
            {"decision": ProjectTopicDecision.APPROVE, "feedback": "Approved."},
            format="json",
        )
        self.assertEqual(review.status_code, status.HTTP_200_OK)

        response = self.client.get("/api/projects/topics/supervised/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], str(topic.pk))
        self.assertEqual(response.data[0]["status"], ProjectTopicStatus.APPROVED)

        queue_response = self.client.get("/api/projects/topics/review-queue/")
        self.assertEqual(queue_response.status_code, status.HTTP_200_OK)
        self.assertEqual(queue_response.data, [])

    def test_previous_supervisor_can_view_topic_they_reviewed_after_reassignment(self):
        topic = self.create_topic()
        self.client.force_authenticate(self.lecturer)
        approve_response = self.client.post(
            f"/api/projects/topics/{topic.pk}/review/",
            {"decision": ProjectTopicDecision.APPROVE, "feedback": "Approved."},
            format="json",
        )
        self.assertEqual(approve_response.status_code, status.HTTP_200_OK)

        reassign_supervisor(
            assignment_id=self.assignment.pk,
            lecturer_id=self.other_lecturer_profile.pk,
            actor=self.coordinator,
            reason="Departmental workload adjustment.",
        )

        previous_supervisor_response = self.client.get("/api/projects/topics/supervised/")
        self.assertEqual(previous_supervisor_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(previous_supervisor_response.data), 1)
        self.assertEqual(previous_supervisor_response.data[0]["id"], str(topic.pk))
        self.assertFalse(previous_supervisor_response.data[0]["can_review"])

        self.client.force_authenticate(self.other_lecturer)
        new_supervisor_response = self.client.get("/api/projects/topics/supervised/")
        self.assertEqual(new_supervisor_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(new_supervisor_response.data), 1)
        self.assertFalse(new_supervisor_response.data[0]["can_review"])

    def test_supervised_topics_are_private_to_the_assigned_supervisor(self):
        topic = self.create_topic()
        self.client.force_authenticate(self.lecturer)
        approve_response = self.client.post(
            f"/api/projects/topics/{topic.pk}/review/",
            {"decision": ProjectTopicDecision.APPROVE, "feedback": "Approved."},
            format="json",
        )
        self.assertEqual(approve_response.status_code, status.HTTP_200_OK)

        self.client.force_authenticate(self.other_lecturer)
        response = self.client.get("/api/projects/topics/supervised/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_coordinator_cannot_access_supervisor_topic_history_endpoint(self):
        self.client.force_authenticate(self.coordinator)
        response = self.client.get("/api/projects/topics/supervised/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_coordinator_cannot_make_supervisor_topic_decision(self):
        topic = self.create_topic()
        self.client.force_authenticate(self.coordinator)
        response = self.client.post(
            f"/api/projects/topics/{topic.pk}/review/",
            {"decision": ProjectTopicDecision.APPROVE, "feedback": "Approved."},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_supervisor_reassignment_transfers_current_topic_review_responsibility(self):
        topic = self.create_topic()
        new_assignment = reassign_supervisor(
            assignment_id=self.assignment.pk,
            lecturer_id=self.other_lecturer_profile.pk,
            actor=self.coordinator,
            reason="Departmental workload adjustment.",
        )
        topic.refresh_from_db()
        self.assignment.refresh_from_db()
        self.assertFalse(self.assignment.is_current)
        self.assertEqual(topic.supervisor_assignment_id, new_assignment.pk)
        self.client.force_authenticate(self.lecturer)
        old_supervisor_response = self.client.get(f"/api/projects/topics/{topic.pk}/")
        self.assertEqual(old_supervisor_response.status_code, status.HTTP_404_NOT_FOUND)
        self.client.force_authenticate(self.other_lecturer)
        new_supervisor_response = self.client.get(f"/api/projects/topics/{topic.pk}/")
        self.assertEqual(new_supervisor_response.status_code, status.HTTP_200_OK)

    def test_rejection_closes_topic_and_allows_new_proposal(self):
        topic = self.create_topic()
        self.client.force_authenticate(self.lecturer)
        response = self.client.post(
            f"/api/projects/topics/{topic.pk}/review/",
            {"decision": ProjectTopicDecision.REJECT, "feedback": "The proposed scope is not suitable."},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        topic.refresh_from_db()
        self.assertFalse(topic.is_current)
        self.assertEqual(topic.status, ProjectTopicStatus.REJECTED)

        self.client.force_authenticate(self.student)
        new_topic = self.client.post("/api/projects/topics/", self.valid_payload, format="json")
        self.assertEqual(new_topic.status_code, status.HTTP_201_CREATED)

    def test_student_cannot_view_another_students_topic(self):
        topic = self.create_topic()
        another_student = self.create_user("another.student@example.com", RoleCode.STUDENT)
        self.client.force_authenticate(another_student)
        response = self.client.get(f"/api/projects/topics/{topic.pk}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def create_topic(self):
        self.client.force_authenticate(self.student)
        response = self.client.post("/api/projects/topics/", self.valid_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return ProjectTopic.objects.get(pk=response.data["id"])
