from unittest.mock import patch

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

from .models import (
    ProjectMilestone,
    ProjectProgressReport,
    ProgressReportStatus,
    ProjectTopic,
    ProjectTopicDecision,
    ProjectTopicRevision,
    ProjectTopicSimilarity,
    ProjectTopicStatus,
    SimilarityAnalysisStatus,
)
from .similarity import analyse_topic_similarity, lexical_similarity

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


class FakeEmbeddingModel:
    def embed(self, texts, batch_size=32):
        for text in texts:
            lowered = text.casefold()
            vector = [0.0] * 384
            if "unrelated-soil-research" in lowered:
                vector[1] = 1.0
            else:
                vector[0] = 1.0
            yield vector


class ProjectTopicSimilarityTests(APITestCase):
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

    def create_topic(self):
        self.client.force_authenticate(self.student)
        response = self.client.post("/api/projects/topics/", self.valid_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return ProjectTopic.objects.get(pk=response.data["id"])

    def create_historical_topic(
        self,
        *,
        session_name="2024/2025",
        status_value=ProjectTopicStatus.APPROVED,
        payload=None,
    ):
        historical_payload = payload or self.valid_payload
        historical_student = self.create_user(
            "historical.student@example.com",
            RoleCode.STUDENT,
        )
        historical_session = AcademicSession.objects.create(
            name=session_name,
            status=AcademicSessionStatus.CLOSED,
        )
        historical_enrollment = StudentEnrollment.objects.create(
            user=historical_student,
            session=historical_session,
            matric_number="CS/2024/009",
            verification_status=StudentVerificationStatus.AUTO_VERIFIED,
            verification_method=VerificationMethod.AUTOMATIC,
        )
        historical_assignment = SupervisorAssignment.objects.create(
            student_enrollment=historical_enrollment,
            lecturer=self.lecturer_profile,
            assigned_by=self.coordinator,
            is_current=False,
        )
        historical_topic = ProjectTopic.objects.create(
            student_enrollment=historical_enrollment,
            supervisor_assignment=historical_assignment,
            title="A Historical Inventory Tracking Platform",
            abstract=historical_payload["abstract"],
            problem_statement=historical_payload["problem_statement"],
            research_objectives=historical_payload["research_objectives"],
            keywords=historical_payload["keywords"],
            status=status_value,
            is_current=status_value != ProjectTopicStatus.REJECTED,
        )
        revision = ProjectTopicRevision.objects.create(
            topic=historical_topic,
            revision_number=1,
            title=historical_topic.title,
            abstract=historical_topic.abstract,
            problem_statement=historical_topic.problem_statement,
            research_objectives=historical_topic.research_objectives,
            keywords=historical_topic.keywords,
            submitted_by=historical_student,
        )
        return historical_topic, revision

    def test_lexical_similarity_detects_shared_terms_and_phrases(self):
        score = lexical_similarity(
            "inventory management stock tracking for retail stores",
            "retail inventory management and stock tracking",
        )
        self.assertGreaterEqual(score, 0.5)

    def test_similarity_analysis_compares_historical_sessions(self):
        topic = self.create_topic()
        historical_topic, historical_revision = self.create_historical_topic()

        with patch(
            "apps.projects.similarity.get_embedding_model",
            return_value=FakeEmbeddingModel(),
        ):
            source_revision = analyse_topic_similarity(topic.pk)

        self.assertEqual(source_revision.similarity_status, SimilarityAnalysisStatus.COMPLETED)
        match = ProjectTopicSimilarity.objects.get(source_revision=source_revision)
        self.assertEqual(match.matched_revision_id, historical_revision.pk)
        self.assertEqual(match.matched_revision.topic.student_enrollment.session.name, "2024/2025")
        self.assertGreaterEqual(match.overall_score, match.threshold)

    def test_similarity_report_is_available_to_current_assigned_supervisor_only(self):
        topic = self.create_topic()
        self.create_historical_topic()
        with patch(
            "apps.projects.similarity.get_embedding_model",
            return_value=FakeEmbeddingModel(),
        ):
            analyse_topic_similarity(topic.pk)

        self.client.force_authenticate(self.lecturer)
        supervisor_response = self.client.get(
            f"/api/projects/topics/{topic.pk}/similarity-report/"
        )
        self.assertEqual(supervisor_response.status_code, status.HTTP_200_OK)
        self.assertEqual(supervisor_response.data["status"], SimilarityAnalysisStatus.COMPLETED)
        self.assertEqual(len(supervisor_response.data["matches"]), 1)
        self.assertEqual(
            supervisor_response.data["matches"][0]["academic_session"],
            "2024/2025",
        )
        self.assertTrue(supervisor_response.data["matches"][0]["matched_sections"])

        UserRole.objects.create(
            user=self.lecturer,
            role=Role.objects.get(code=RoleCode.PROJECT_COORDINATOR),
        )
        dual_role_response = self.client.get(
            f"/api/projects/topics/{topic.pk}/similarity-report/"
        )
        self.assertEqual(dual_role_response.status_code, status.HTTP_403_FORBIDDEN)
        UserRole.objects.filter(
            user=self.lecturer,
            role__code=RoleCode.PROJECT_COORDINATOR,
        ).delete()

        self.client.force_authenticate(self.student)
        student_response = self.client.get(
            f"/api/projects/topics/{topic.pk}/similarity-report/"
        )
        self.assertEqual(student_response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(self.coordinator)
        coordinator_response = self.client.get(
            f"/api/projects/topics/{topic.pk}/similarity-report/"
        )
        self.assertEqual(coordinator_response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(self.other_lecturer)
        other_supervisor_response = self.client.get(
            f"/api/projects/topics/{topic.pk}/similarity-report/"
        )
        self.assertEqual(other_supervisor_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_similarity_analysis_excludes_the_same_student_from_historical_matches(self):
        topic = self.create_topic()
        historical_student = self.student
        old_session = AcademicSession.objects.create(
            name="2023/2024",
            status=AcademicSessionStatus.CLOSED,
        )
        old_enrollment = StudentEnrollment.objects.create(
            user=historical_student,
            session=old_session,
            matric_number="CS/2023/001",
            verification_status=StudentVerificationStatus.AUTO_VERIFIED,
            verification_method=VerificationMethod.AUTOMATIC,
        )
        old_assignment = SupervisorAssignment.objects.create(
            student_enrollment=old_enrollment,
            lecturer=self.lecturer_profile,
            assigned_by=self.coordinator,
            is_current=False,
        )
        old_topic = ProjectTopic.objects.create(
            student_enrollment=old_enrollment,
            supervisor_assignment=old_assignment,
            title="The same student's earlier proposal",
            abstract=self.valid_payload["abstract"],
            problem_statement=self.valid_payload["problem_statement"],
            research_objectives=self.valid_payload["research_objectives"],
            keywords=self.valid_payload["keywords"],
            status=ProjectTopicStatus.REJECTED,
            is_current=False,
        )
        ProjectTopicRevision.objects.create(
            topic=old_topic,
            revision_number=1,
            title=old_topic.title,
            abstract=old_topic.abstract,
            problem_statement=old_topic.problem_statement,
            research_objectives=old_topic.research_objectives,
            keywords=old_topic.keywords,
            submitted_by=self.student,
        )

        with patch(
            "apps.projects.similarity.get_embedding_model",
            return_value=FakeEmbeddingModel(),
        ):
            source_revision = analyse_topic_similarity(topic.pk)

        self.assertEqual(
            ProjectTopicSimilarity.objects.filter(source_revision=source_revision).count(),
            0,
        )

    def test_similarity_check_can_be_retried_by_current_supervisor(self):
        topic = self.create_topic()
        self.create_historical_topic()
        self.client.force_authenticate(self.lecturer)
        with patch(
            "apps.projects.similarity.get_embedding_model",
            return_value=FakeEmbeddingModel(),
        ):
            response = self.client.post(
                f"/api/projects/topics/{topic.pk}/run-similarity/",
                {},
                format="json",
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], SimilarityAnalysisStatus.COMPLETED)
        self.assertEqual(len(response.data["matches"]), 1)


    def test_rejected_historical_topics_are_included_in_similarity_comparison(self):
        topic = self.create_topic()
        historical_topic, historical_revision = self.create_historical_topic(
            status_value=ProjectTopicStatus.REJECTED,
        )
        with patch(
            "apps.projects.similarity.get_embedding_model",
            return_value=FakeEmbeddingModel(),
        ):
            source_revision = analyse_topic_similarity(topic.pk)

        match = ProjectTopicSimilarity.objects.get(source_revision=source_revision)
        self.assertEqual(match.matched_revision_id, historical_revision.pk)
        self.assertEqual(match.matched_revision.topic.status, ProjectTopicStatus.REJECTED)

    def test_unrelated_historical_topics_below_threshold_are_not_flagged(self):
        topic = self.create_topic()
        unrelated_payload = {
            "title": "Unrelated soil science research",
            "abstract": "unrelated-soil-research examines soil nutrients and crop yield.",
            "problem_statement": "unrelated-soil-research studies soil erosion in farmland.",
            "research_objectives": "unrelated-soil-research measures soil composition and crop growth.",
            "keywords": ["unrelated-soil-research", "soil science", "crop yield"],
        }
        self.create_historical_topic(payload=unrelated_payload)
        with patch(
            "apps.projects.similarity.get_embedding_model",
            return_value=FakeEmbeddingModel(),
        ):
            source_revision = analyse_topic_similarity(topic.pk)

        self.assertEqual(source_revision.similarity_status, SimilarityAnalysisStatus.COMPLETED)
        self.assertEqual(
            ProjectTopicSimilarity.objects.filter(source_revision=source_revision).count(),
            0,
        )

    def test_previous_supervisor_cannot_access_similarity_report_after_reassignment(self):
        topic = self.create_topic()
        self.create_historical_topic()
        with patch(
            "apps.projects.similarity.get_embedding_model",
            return_value=FakeEmbeddingModel(),
        ):
            analyse_topic_similarity(topic.pk)

        reassign_supervisor(
            assignment_id=self.assignment.pk,
            lecturer_id=self.other_lecturer_profile.pk,
            actor=self.coordinator,
            reason="Departmental workload adjustment.",
        )

        self.client.force_authenticate(self.lecturer)
        old_supervisor_response = self.client.get(
            f"/api/projects/topics/{topic.pk}/similarity-report/"
        )
        self.assertEqual(old_supervisor_response.status_code, status.HTTP_404_NOT_FOUND)

        self.client.force_authenticate(self.other_lecturer)
        new_supervisor_response = self.client.get(
            f"/api/projects/topics/{topic.pk}/similarity-report/"
        )
        self.assertEqual(new_supervisor_response.status_code, status.HTTP_200_OK)


    def test_semantic_similarity_can_flag_proposals_with_different_wording(self):
        topic = self.create_topic()
        paraphrased_payload = {
            "title": "Digital stock records for independent shops",
            "abstract": "A digital tool will help small shops monitor goods and maintain accurate stock information.",
            "problem_statement": "Shop operators struggle to know which products remain available when records are maintained manually.",
            "research_objectives": "The work will examine shop inventory practices and create a digital method for tracking products.",
            "keywords": ["shop operations", "goods monitoring", "product records"],
        }
        self.create_historical_topic(payload=paraphrased_payload)
        with patch(
            "apps.projects.similarity.get_embedding_model",
            return_value=FakeEmbeddingModel(),
        ):
            source_revision = analyse_topic_similarity(topic.pk)

        self.assertEqual(
            ProjectTopicSimilarity.objects.filter(source_revision=source_revision).count(),
            1,
        )


class ProjectMilestoneAndProgressAPITests(APITestCase):
    def setUp(self):
        self.student = self.create_user("progress.student@example.com", RoleCode.STUDENT)
        self.lecturer = self.create_user("progress.supervisor@example.com", RoleCode.LECTURER)
        self.other_lecturer = self.create_user("progress.other@example.com", RoleCode.LECTURER)
        self.coordinator = self.create_user("progress.coordinator@example.com", RoleCode.PROJECT_COORDINATOR)
        self.administrator = self.create_user("progress.admin@example.com", RoleCode.ADMINISTRATOR)
        self.session = AcademicSession.objects.create(
            name="2027/2028",
            status=AcademicSessionStatus.ACTIVE,
        )
        self.enrollment = StudentEnrollment.objects.create(
            user=self.student,
            session=self.session,
            matric_number="CS/2027/PROGRESS001",
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
        self.milestone = ProjectMilestone.objects.create(
            session=self.session,
            title="Literature review",
            description="Review relevant academic literature.",
            expected_achievement="A documented review of relevant sources.",
            sequence=1,
            created_by=self.coordinator,
            updated_by=self.coordinator,
        )
        self.report_payload = {
            "completed_activities": "Reviewed twelve relevant journal articles and identified the research gap.",
            "challenges": "Access to two full-text papers was limited.",
            "next_steps": "Complete the synthesis and prepare the literature review chapter.",
        }

    def create_user(self, email, role_code):
        user = User.objects.create_user(
            email=email,
            password="Strong-test-password-123",
            first_name="Progress",
            last_name="Tester",
        )
        role = Role.objects.get(code=role_code)
        UserRole.objects.create(user=user, role=role)
        return user

    def submit_report(self):
        self.client.force_authenticate(self.student)
        response = self.client.post(
            "/api/projects/progress-reports/",
            {"milestone": str(self.milestone.pk), **self.report_payload},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return ProjectProgressReport.objects.get(pk=response.data["id"])

    def test_coordinator_can_create_milestone_and_students_can_view_session_milestones(self):
        self.client.force_authenticate(self.coordinator)
        response = self.client.post(
            "/api/projects/milestones/",
            {
                "session": str(self.session.pk),
                "title": "System design",
                "description": "Prepare the system analysis and design.",
                "expected_achievement": "Approved design specification.",
                "sequence": 2,
                "due_date": "2027-04-30",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.client.force_authenticate(self.student)
        response = self.client.get("/api/projects/milestones/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_only_coordinator_can_create_milestones(self):
        self.client.force_authenticate(self.lecturer)
        response = self.client.post(
            "/api/projects/milestones/",
            {
                "session": str(self.session.pk),
                "title": "System design",
                "sequence": 2,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_student_can_submit_progress_report_for_assigned_milestone(self):
        report = self.submit_report()
        self.assertEqual(report.status, ProgressReportStatus.SUBMITTED)
        self.assertEqual(report.revisions.count(), 1)
        self.assertEqual(report.supervisor_assignment_id, self.assignment.pk)

    def test_student_cannot_submit_without_supervisor(self):
        self.assignment.is_current = False
        self.assignment.save(update_fields=["is_current"])
        self.client.force_authenticate(self.student)
        response = self.client.post(
            "/api/projects/progress-reports/",
            {"milestone": str(self.milestone.pk), **self.report_payload},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_supervisor_can_view_and_review_assigned_student_progress(self):
        report = self.submit_report()
        self.client.force_authenticate(self.lecturer)
        response = self.client.get("/api/projects/progress-reports/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item["id"] for item in response.data], [str(report.pk)])

        review = self.client.post(
            f"/api/projects/progress-reports/{report.pk}/review/",
            {
                "decision": "review",
                "assessment": "on_track",
                "feedback": "Progress is satisfactory. Continue with the planned activities.",
            },
            format="json",
        )
        self.assertEqual(review.status_code, status.HTTP_200_OK)
        report.refresh_from_db()
        self.assertEqual(report.status, ProgressReportStatus.REVIEWED)
        self.assertEqual(report.reviews.count(), 1)

    def test_other_supervisor_cannot_view_or_review_progress_report(self):
        report = self.submit_report()
        self.client.force_authenticate(self.other_lecturer)
        response = self.client.get(f"/api/projects/progress-reports/{report.pk}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        review = self.client.post(
            f"/api/projects/progress-reports/{report.pk}/review/",
            {
                "decision": "review",
                "assessment": "on_track",
                "feedback": "Reviewed.",
            },
            format="json",
        )
        self.assertEqual(review.status_code, status.HTTP_404_NOT_FOUND)

    def test_supervisor_can_request_revision_and_student_can_resubmit(self):
        report = self.submit_report()
        self.client.force_authenticate(self.lecturer)
        response = self.client.post(
            f"/api/projects/progress-reports/{report.pk}/review/",
            {
                "decision": "request_revision",
                "assessment": "needs_attention",
                "feedback": "Please provide more detail about the research gap.",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        report.refresh_from_db()
        self.assertEqual(report.status, ProgressReportStatus.REVISION_REQUESTED)

        self.client.force_authenticate(self.student)
        response = self.client.post(
            f"/api/projects/progress-reports/{report.pk}/resubmit/",
            {
                "completed_activities": "Expanded the review and clarified the research gap.",
                "challenges": "No significant challenges.",
                "next_steps": "Prepare the conceptual framework.",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        report.refresh_from_db()
        self.assertEqual(report.status, ProgressReportStatus.SUBMITTED)
        self.assertEqual(report.revisions.count(), 2)
        self.assertEqual(report.reviews.count(), 1)

    def test_coordinator_cannot_view_student_progress_reports(self):
        self.submit_report()
        self.client.force_authenticate(self.coordinator)
        response = self.client.get("/api/projects/progress-reports/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_student_cannot_view_another_students_progress_report(self):
        report = self.submit_report()
        another_student = self.create_user("progress.other.student@example.com", RoleCode.STUDENT)
        self.client.force_authenticate(another_student)
        response = self.client.get(f"/api/projects/progress-reports/{report.pk}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_milestone_sequence_must_be_unique_within_session(self):
        self.client.force_authenticate(self.coordinator)
        response = self.client.post(
            "/api/projects/milestones/",
            {
                "session": str(self.session.pk),
                "title": "System analysis",
                "sequence": 1,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_progress_report_cannot_be_submitted_for_closed_session(self):
        self.session.status = AcademicSessionStatus.CLOSED
        self.session.save(update_fields=["status"])
        self.client.force_authenticate(self.student)
        response = self.client.post(
            "/api/projects/progress-reports/",
            {"milestone": str(self.milestone.pk), **self.report_payload},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_milestone_structure_is_immutable_after_a_report_is_submitted(self):
        self.submit_report()
        self.client.force_authenticate(self.coordinator)
        response = self.client.patch(
            f"/api/projects/milestones/{self.milestone.pk}/",
            {"title": "Revised milestone title"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


    def test_administrator_without_project_coordinator_role_cannot_manage_milestones(self):
        self.client.force_authenticate(self.administrator)
        response = self.client.post(
            "/api/projects/milestones/",
            {
                "session": str(self.session.pk),
                "title": "System design",
                "sequence": 2,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
