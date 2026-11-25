from datetime import timedelta
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import Role, RoleCode, User, UserRole
from apps.academics.models import AcademicSession, LecturerProfile, StudentEnrollment, SupervisorAssignment
from apps.academics.services import reassign_supervisor
from .models import (
    AssessmentScheme, CompletionEvent, DeadlineExtension, DefencePanel, ExaminerScore, ProjectCompletion,
    ProjectNotification, ProjectReportSection, ProjectReportSubmission, ProjectTopic,
)


class CompletionWorkflowTests(APITestCase):
    url = "/api/projects/completion/"

    def setUp(self):
        self.session = AcademicSession.objects.create(name="Test session", status="active")
        self.student = self.user("student", RoleCode.STUDENT)
        self.coordinator = self.user("coordinator", RoleCode.PROJECT_COORDINATOR)
        self.supervisor = self.user("supervisor", RoleCode.LECTURER)
        self.examiner_one = self.user("examiner-one", RoleCode.LECTURER)
        self.examiner_two = self.user("examiner-two", RoleCode.LECTURER)
        self.outsider = self.user("outsider", RoleCode.STUDENT)
        self.supervisor_profile = LecturerProfile.objects.create(user=self.supervisor)
        self.profile_one = LecturerProfile.objects.create(user=self.examiner_one)
        self.profile_two = LecturerProfile.objects.create(user=self.examiner_two)
        self.enrollment = StudentEnrollment.objects.create(user=self.student, session=self.session, matric_number="TEST/01", verification_status="auto_verified")
        self.assignment = SupervisorAssignment.objects.create(student_enrollment=self.enrollment, lecturer=self.supervisor_profile, assigned_by=self.coordinator)
        self.section = ProjectReportSection.objects.create(session=self.session, title="Chapter One", sequence=1, created_by=self.coordinator, updated_by=self.coordinator)
        self.components = [{"name": "Report", "maximum": 60}, {"name": "Defence", "maximum": 40}]

    def user(self, name, role):
        user = User.objects.create_user(email=f"{name}@example.com", first_name=name)
        UserRole.objects.create(user=user, role=Role.objects.get(code=role))
        return user

    def action(self, user, action, expected=200, **kwargs):
        self.client.force_authenticate(user)
        data = {"session": str(self.session.pk), "action": action, **kwargs}
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, expected, response.data)
        return response

    def workspace(self, user):
        self.client.force_authenticate(user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200, response.data)
        return response.data["workspace"]

    def make_pdf(self, name="Final report.pdf"):
        return SimpleUploadedFile(name, b"%PDF-1.7\n%%EOF", content_type="application/pdf")

    def ready_to_submit(self):
        ProjectTopic.objects.create(student_enrollment=self.enrollment, supervisor_assignment=self.assignment, title="Test project", abstract="Test", problem_statement="Test", research_objectives="Test", keywords=["test"], status="approved")
        ProjectReportSubmission.objects.create(student_enrollment=self.enrollment, supervisor_assignment=self.assignment, section=self.section, status="approved")

    def upload(self, expected=200):
        self.client.force_authenticate(self.student)
        response = self.client.post(self.url, {"action": "submit", "session": str(self.session.pk), "file": self.make_pdf()}, format="multipart")
        self.assertEqual(response.status_code, expected, response.data)

    def allocate(self):
        project = ProjectCompletion.objects.create(enrollment=self.enrollment, status="cleared")
        self.action(self.supervisor, "save_scheme", components=self.components)
        self.action(self.coordinator, "create_panel", name="Panel A", members=[str(self.profile_one.pk), str(self.profile_two.pk)])
        panel = DefencePanel.objects.get(name="Panel A")
        params = {"project": str(project.pk), "panel": str(panel.pk), "defence_at": (timezone.now() + timedelta(days=1)).isoformat(), "venue": "Room 1"}
        self.action(self.coordinator, "schedule", **params)
        ProjectCompletion.objects.filter(pk=project.pk).update(defence_at=timezone.now() - timedelta(minutes=1))
        project.refresh_from_db()
        return project

    @patch("apps.projects.lifecycle.upload_report_document")
    def test_final_submission_requires_approvals_and_preserves_versions(self, upload):
        self.upload(expected=400)
        self.ready_to_submit()
        self.upload()
        project = ProjectCompletion.objects.get(enrollment=self.enrollment)
        self.assertEqual(project.documents.get().original_filename, "Final report.pdf")
        self.action(self.examiner_one, "recommend", expected=403, project=str(project.pk))
        self.action(self.supervisor, "decline", project=str(project.pk), note="Revise the final chapter")
        self.upload()
        self.assertEqual(project.documents.count(), 2)
        self.action(self.supervisor, "recommend", project=str(project.pk))
        self.action(self.coordinator, "clear", project=str(project.pk))
        project.refresh_from_db()
        self.assertEqual(project.status, "cleared")
        self.assertIsNone(self.workspace(self.outsider))
        self.assertEqual(upload.call_count, 2)

    def test_deadline_extension_changes_only_approved_student_deadline(self):
        due = timezone.localdate() + timedelta(days=3)
        new_date = due + timedelta(days=7)
        self.action(self.student, "set_deadline", expected=403, kind="topic", due_date=due.isoformat())
        self.action(self.coordinator, "set_deadline", kind="topic", due_date=due.isoformat())
        self.action(self.student, "request_extension", kind="topic", requested_date=new_date.isoformat(), justification="Illness")
        extension = DeadlineExtension.objects.get()
        self.assertEqual(str(self.workspace(self.student)["deadlines"][0]["effective_date"]), due.isoformat())
        self.action(self.coordinator, "approve_extension", extension=str(extension.pk))
        deadline = self.workspace(self.student)["deadlines"][0]
        self.assertEqual(str(deadline["due_date"]), due.isoformat())
        self.assertEqual(str(deadline["effective_date"]), new_date.isoformat())
        self.assertTrue(ProjectNotification.objects.filter(recipient=self.student, category="deadlines").exists())

    def test_panel_rejects_current_supervisor_and_rubric_must_total_100(self):
        project = ProjectCompletion.objects.create(enrollment=self.enrollment, status="cleared")
        self.action(self.supervisor, "save_scheme", expected=400, components=[{"name": "Report", "maximum": 99}])
        self.action(self.supervisor, "save_scheme", components=self.components)
        self.action(self.coordinator, "create_panel", name="Conflicting panel", members=[str(self.supervisor_profile.pk), str(self.profile_one.pk)])
        panel = DefencePanel.objects.get()
        self.action(self.coordinator, "schedule", expected=400, project=str(project.pk), panel=str(panel.pk), defence_at=(timezone.now() + timedelta(days=1)).isoformat(), venue="Hall")
        project.refresh_from_db()
        self.assertIsNone(project.panel_id)

    def test_former_supervisor_cannot_be_allocated_as_an_examiner(self):
        replacement = self.user("replacement-supervisor", RoleCode.LECTURER)
        replacement_profile = LecturerProfile.objects.create(user=replacement)
        reassign_supervisor(
            assignment_id=self.assignment.pk,
            lecturer_id=replacement_profile.pk,
            actor=self.coordinator,
            reason="Workload redistribution.",
        )
        project = ProjectCompletion.objects.create(enrollment=self.enrollment, status="cleared")
        self.action(replacement, "save_scheme", components=self.components)
        self.action(
            self.coordinator,
            "create_panel",
            name="Former supervisor conflict",
            members=[str(self.supervisor_profile.pk), str(self.profile_one.pk)],
        )
        panel = DefencePanel.objects.get(name="Former supervisor conflict")
        self.action(
            self.coordinator,
            "schedule",
            expected=400,
            project=str(project.pk),
            panel=str(panel.pk),
            defence_at=(timezone.now() + timedelta(days=1)).isoformat(),
            venue="Room 1",
        )
        project.refresh_from_db()
        self.assertIsNone(project.panel_id)

    def test_coordinator_who_examined_project_cannot_approve_result(self):
        coordinator_examiner = self.user("coordinator-examiner", RoleCode.PROJECT_COORDINATOR)
        UserRole.objects.create(
            user=coordinator_examiner,
            role=Role.objects.get(code=RoleCode.LECTURER),
        )
        coordinator_examiner_profile = LecturerProfile.objects.create(user=coordinator_examiner)
        project = ProjectCompletion.objects.create(enrollment=self.enrollment, status="cleared")
        self.action(self.supervisor, "save_scheme", components=self.components)
        self.action(
            self.coordinator,
            "create_panel",
            name="Coordinator examiner panel",
            members=[str(coordinator_examiner_profile.pk), str(self.profile_two.pk)],
        )
        panel = DefencePanel.objects.get(name="Coordinator examiner panel")
        self.action(
            self.coordinator,
            "schedule",
            project=str(project.pk),
            panel=str(panel.pk),
            defence_at=(timezone.now() + timedelta(days=1)).isoformat(),
            venue="Room 2",
        )
        ProjectCompletion.objects.filter(pk=project.pk).update(
            defence_at=timezone.now() - timedelta(minutes=1)
        )
        self.action(coordinator_examiner, "score", project=str(project.pk), marks=[50, 30])
        self.action(self.examiner_two, "score", project=str(project.pk), marks=[40, 20])
        self.action(
            coordinator_examiner,
            "approve_result",
            expected=403,
            project=str(project.pk),
        )
        coordinator_project = self.workspace(coordinator_examiner)["projects"][0]
        self.assertNotIn("approve_result", coordinator_project["actions"])
        self.action(
            coordinator_examiner,
            "return_result",
            expected=403,
            project=str(project.pk),
            note="Examiner cannot return own result.",
        )
        self.action(self.coordinator, "approve_result", project=str(project.pk))
        self.action(
            coordinator_examiner,
            "publish",
            expected=403,
            project=str(project.pk),
        )
        self.action(self.coordinator, "publish", project=str(project.pk))
        self.action(
            self.student,
            "appeal",
            project=str(project.pk),
            complaint="Please review the published assessment.",
        )
        appeal = project.appeals.get()
        self.action(
            coordinator_examiner,
            "review_appeal",
            project=str(project.pk),
            appeal=str(appeal.pk),
            note="Panel has reviewed the appeal.",
        )
        self.action(
            coordinator_examiner,
            "accept_appeal",
            expected=403,
            project=str(project.pk),
            appeal=str(appeal.pk),
            note="Examiner cannot decide own appeal.",
        )
        self.action(
            self.coordinator,
            "accept_appeal",
            project=str(project.pk),
            appeal=str(appeal.pk),
            note="Independent Coordinator decision.",
        )

    def test_former_supervisor_cannot_score_an_existing_conflicted_panel(self):
        replacement = self.user("replacement-supervisor-score", RoleCode.LECTURER)
        replacement_profile = LecturerProfile.objects.create(user=replacement)
        reassign_supervisor(
            assignment_id=self.assignment.pk,
            lecturer_id=replacement_profile.pk,
            actor=self.coordinator,
            reason="Supervisor reassignment.",
        )
        panel = DefencePanel.objects.create(
            session=self.session,
            name="Legacy conflicted panel",
            created_by=self.coordinator,
        )
        panel.members.set([self.supervisor_profile, self.profile_one])
        project = ProjectCompletion.objects.create(
            enrollment=self.enrollment,
            status="scheduled",
            panel=panel,
            defence_at=timezone.now() - timedelta(minutes=1),
            components=self.components,
        )
        self.action(
            self.supervisor,
            "score",
            expected=403,
            project=str(project.pk),
            marks=[50, 30],
        )
        self.assertEqual(self.workspace(self.supervisor)["projects"], [])

    def test_coordinator_can_reallocate_panel_without_deleting_previous_score_round(self):
        project = ProjectCompletion.objects.create(
            enrollment=self.enrollment,
            status="panel_reallocation_required",
            score_round=2,
        )
        ExaminerScore.objects.create(
            project=project,
            examiner=self.profile_one,
            round=1,
            marks=["50.00", "30.00"],
        )
        self.action(self.supervisor, "save_scheme", components=self.components)
        self.action(
            self.coordinator,
            "create_panel",
            name="Replacement panel",
            members=[str(self.profile_one.pk), str(self.profile_two.pk)],
        )
        panel = DefencePanel.objects.get(name="Replacement panel")
        coordinator_project = self.workspace(self.coordinator)["projects"][0]
        self.assertIn("schedule", coordinator_project["actions"])
        student_project = self.workspace(self.student)["projects"][0]
        self.assertEqual(student_project["status"], "panel_reallocation_required")
        self.assertEqual(student_project["published_result"], {})
        self.action(
            self.coordinator,
            "schedule",
            project=str(project.pk),
            panel=str(panel.pk),
            defence_at=(timezone.now() + timedelta(days=1)).isoformat(),
            venue="Replacement venue",
        )
        project.refresh_from_db()
        self.assertEqual(project.status, "scheduled")
        self.assertEqual(project.score_round, 2)
        self.assertEqual(project.scores.count(), 1)
        ProjectCompletion.objects.filter(pk=project.pk).update(
            defence_at=timezone.now() - timedelta(minutes=1)
        )
        self.action(self.examiner_one, "score", project=str(project.pk), marks=[55, 35])
        self.assertEqual(project.scores.filter(round=2).count(), 1)

    def test_closed_session_panel_reallocation_setup_remains_coordinator_only(self):
        project = ProjectCompletion.objects.create(
            enrollment=self.enrollment,
            status="panel_reallocation_required",
            score_round=2,
        )
        CompletionEvent.objects.create(
            project=project,
            actor=self.coordinator,
            action="panel_reallocation_required",
            note="A replacement panel is required.",
        )
        AcademicSession.objects.filter(pk=self.session.pk).update(status="closed")

        self.action(
            self.supervisor,
            "create_panel",
            expected=400,
            name="Unauthorised replacement panel",
            members=[str(self.profile_one.pk), str(self.profile_two.pk)],
        )
        self.assertFalse(
            DefencePanel.objects.filter(name="Unauthorised replacement panel").exists()
        )

    def test_panel_reallocation_can_finish_in_a_closed_session(self):
        project = ProjectCompletion.objects.create(
            enrollment=self.enrollment,
            status="panel_reallocation_required",
            score_round=2,
        )
        CompletionEvent.objects.create(
            project=project,
            actor=self.coordinator,
            action="panel_reallocation_required",
            note="A replacement panel is required.",
        )
        self.assignment.is_current = False
        self.assignment.ended_at = timezone.now()
        self.assignment.ended_by = self.coordinator
        self.assignment.save(update_fields=["is_current", "ended_at", "ended_by"])
        AcademicSession.objects.filter(pk=self.session.pk).update(status="closed")
        replacement_supervisor = self.user(
            "closed-session-replacement-supervisor",
            RoleCode.LECTURER,
        )
        replacement_profile = LecturerProfile.objects.create(
            user=replacement_supervisor,
            staff_number="CLOSED-REASSIGN-001",
        )
        from apps.academics.services import assign_supervisor

        assign_supervisor(
            enrollment_id=self.enrollment.pk,
            lecturer_id=replacement_profile.pk,
            actor=self.coordinator,
        )
        self.action(replacement_supervisor, "save_scheme", components=self.components)
        self.action(
            self.coordinator,
            "create_panel",
            name="Closed-session replacement panel",
            members=[str(self.profile_one.pk), str(self.profile_two.pk)],
        )
        panel = DefencePanel.objects.get(name="Closed-session replacement panel")
        self.action(
            self.coordinator,
            "schedule",
            project=str(project.pk),
            panel=str(panel.pk),
            defence_at=(timezone.now() + timedelta(days=1)).isoformat(),
            venue="Closed-session venue",
        )
        ProjectCompletion.objects.filter(pk=project.pk).update(
            defence_at=timezone.now() - timedelta(minutes=1)
        )
        self.action(self.examiner_one, "score", project=str(project.pk), marks=[50, 30])
        self.action(self.examiner_two, "score", project=str(project.pk), marks=[40, 20])
        self.action(self.coordinator, "approve_result", project=str(project.pk))
        self.action(self.coordinator, "publish", project=str(project.pk))
        project.refresh_from_db()
        self.assertEqual(project.status, "published")
        self.assertIsNotNone(project.published_at)

    def test_scores_publication_corrections_and_appeal(self):
        project = self.allocate()
        pk = str(project.pk)
        self.action(self.supervisor, "score", expected=403, project=pk, marks=[50, 30])
        self.action(self.examiner_one, "score", expected=400, project=pk, marks=[61, 20])
        self.action(self.examiner_one, "score", project=pk, marks=[50, 30])
        self.action(self.examiner_one, "score", expected=400, project=pk, marks=[30, 20])
        self.action(self.coordinator, "approve_result", expected=400, project=pk)
        self.assertNotIn("my_marks", self.workspace(self.student)["projects"][0])
        self.assertEqual(self.workspace(self.examiner_two)["projects"][0]["my_marks"], [])
        self.assertEqual(self.workspace(self.student)["projects"][0]["published_result"], {})
        self.action(self.examiner_two, "score", project=pk, marks=[40, 20])
        self.action(self.coordinator, "return_result", project=pk, note="Verify calculation")
        self.action(self.examiner_one, "score", project=pk, marks=[50, 30])
        self.action(self.coordinator, "approve_result", expected=400, project=pk)
        self.action(self.examiner_two, "score", project=pk, marks=[40, 20])
        self.action(self.coordinator, "approve_result", project=pk)
        self.assertEqual(self.workspace(self.student)["projects"][0]["published_result"], {})
        self.action(self.coordinator, "publish", project=pk)
        result = self.workspace(self.student)["projects"][0]["published_result"]
        self.assertEqual(result["overall"], "70.00")
        self.assertEqual(result["components"][0]["average"], "45.00")
        self.action(self.student, "appeal", project=pk, complaint="Please verify the report mark.")
        appeal = project.appeals.get()
        self.action(self.coordinator, "accept_appeal", expected=400, project=pk, appeal=str(appeal.pk), note="Accepted")
        self.action(self.examiner_one, "review_appeal", project=pk, appeal=str(appeal.pk), note="Panel recommends correction")
        self.action(self.coordinator, "accept_appeal", project=pk, appeal=str(appeal.pk), note="Accepted")
        self.assertEqual(self.workspace(self.student)["projects"][0]["published_result"]["overall"], "70.00")
        self.action(self.examiner_one, "score", project=pk, marks=[60, 30])
        self.action(self.examiner_two, "score", project=pk, marks=[40, 20])
        self.action(self.coordinator, "approve_result", project=pk)
        self.action(self.coordinator, "publish", project=pk)
        self.assertEqual(self.workspace(self.student)["projects"][0]["published_result"]["overall"], "75.00")
        self.assertEqual(ExaminerScore.objects.count(), 6)

    def test_appeal_window_expires(self):
        project = ProjectCompletion.objects.create(enrollment=self.enrollment, status="published", published_at=timezone.now() - timedelta(days=15))
        self.action(self.student, "appeal", expected=400, project=str(project.pk), complaint="Late appeal")

    def test_notification_preferences_and_read_permissions(self):
        notification = ProjectNotification.objects.create(recipient=self.student, category="reports", message="A report is ready.")
        self.client.force_authenticate(self.outsider)
        response = self.client.post("/api/projects/notifications/", {"action": "mark_read", "id": str(notification.pk)}, format="json")
        self.assertEqual(response.status_code, 200)
        notification.refresh_from_db()
        self.assertIsNone(notification.read_at)
        self.client.force_authenticate(self.student)
        response = self.client.get("/api/projects/notifications/")
        preferences = response.data["preferences"]
        preferences["reports"]["in_app"] = False
        response = self.client.post("/api/projects/notifications/", {"action": "preferences", "preferences": preferences}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["preferences"]["reports"]["in_app"])
        self.client.post("/api/projects/notifications/", {"action": "mark_read"}, format="json")
        notification.refresh_from_db()
        self.assertIsNotNone(notification.read_at)

    @patch("apps.projects.report_views.create_report_download_url", return_value="https://storage.example/download")
    @patch("apps.projects.lifecycle.upload_report_document")
    @patch("apps.projects.report_services.upload_report_document")
    def test_annotated_feedback_is_private_and_downloadable(self, report_upload, annotation_upload, sign):
        self.client.force_authenticate(self.student)
        response = self.client.post("/api/projects/report-submissions/", {"section": str(self.section.pk), "file": self.make_pdf("Chapter One.pdf")}, format="multipart")
        self.assertEqual(response.status_code, 201, response.data)
        submission = ProjectReportSubmission.objects.get(pk=response.data["id"])
        self.client.force_authenticate(self.supervisor)
        response = self.client.post(f"/api/projects/report-submissions/{submission.pk}/review/", {"decision": "request_revision", "feedback": "See annotated copy", "annotation": self.make_pdf("Corrections.pdf")}, format="multipart")
        self.assertEqual(response.status_code, 200, response.data)
        review = response.data["reviews"][0]
        self.assertEqual(review["annotation_filename"], "Corrections.pdf")
        self.client.force_authenticate(self.student)
        response = self.client.get(review["annotation_download_path"])
        self.assertEqual(response.status_code, 200, response.data)
        self.client.force_authenticate(self.outsider)
        self.assertEqual(self.client.get(review["annotation_download_path"]).status_code, 404)

    @patch("apps.projects.lifecycle_views.create_report_download_url", return_value="https://storage.example/signed-final")
    @patch("apps.projects.lifecycle.upload_report_document")
    def test_final_document_download_is_scoped(self, upload, sign):
        self.ready_to_submit()
        self.upload()
        project = ProjectCompletion.objects.get(enrollment=self.enrollment)
        document = project.documents.get()
        url = f"/api/projects/final-documents/{document.pk}/download/"
        for actor in [self.student, self.supervisor, self.coordinator]:
            self.client.force_authenticate(actor)
            self.assertEqual(self.client.get(url).status_code, 200)
        for actor in [self.outsider, self.examiner_one]:
            self.client.force_authenticate(actor)
            self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(sign.call_count, 3)

    def test_eligible_published_result_appeal_survives_session_closure(self):
        project = ProjectCompletion.objects.create(enrollment=self.enrollment, status="published", published_at=timezone.now())
        AcademicSession.objects.filter(pk=self.session.pk).update(status="closed")
        self.action(self.student, "appeal", project=str(project.pk), complaint="Check the marks")
        self.assertEqual(project.appeals.count(), 1)
        self.action(self.coordinator, "set_deadline", expected=400, kind="topic", due_date=timezone.localdate().isoformat())
