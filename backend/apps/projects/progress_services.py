from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.academics.models import (
    AcademicSessionStatus,
    StudentEnrollment,
    StudentVerificationStatus,
    SupervisorAssignment,
)

from .models import (
    ProjectMilestone,
    ProjectProgressReport,
    ProjectProgressRevision,
    ProgressReportStatus,
)

VERIFIED_STATUSES = (
    StudentVerificationStatus.AUTO_VERIFIED,
    StudentVerificationStatus.MANUALLY_APPROVED,
)


def _current_assignment(enrollment, actor=None):
    assignments = SupervisorAssignment.objects.select_related(
        "lecturer__user"
    ).filter(
        student_enrollment=enrollment,
        is_current=True,
        lecturer__is_active=True,
        lecturer__user__is_active=True,
    )
    if actor is not None:
        assignments = assignments.filter(lecturer__user=actor)
    return assignments.first()


@transaction.atomic
def submit_progress_report(*, actor, milestone_id, data):
    milestone = ProjectMilestone.objects.select_for_update().select_related(
        "session"
    ).get(pk=milestone_id)
    if not milestone.is_active:
        raise ValidationError("This project milestone is no longer accepting reports.")
    if milestone.session.status != AcademicSessionStatus.ACTIVE:
        raise ValidationError("Progress reports can only be submitted during an active academic session.")

    enrollment = StudentEnrollment.objects.select_for_update().filter(
        user=actor,
        session=milestone.session,
        verification_status__in=VERIFIED_STATUSES,
    ).first()
    if enrollment is None:
        raise ValidationError("A verified student registration is required for this milestone.")

    assignment = _current_assignment(enrollment)
    if assignment is None:
        raise ValidationError("A supervisor must be assigned before submitting a progress report.")

    if ProjectProgressReport.objects.filter(
        milestone=milestone,
        student_enrollment=enrollment,
    ).exists():
        raise ValidationError("A progress report already exists for this milestone. Use the revision option if your supervisor requested changes.")

    try:
        with transaction.atomic():
            report = ProjectProgressReport.objects.create(
                milestone=milestone,
                student_enrollment=enrollment,
                supervisor_assignment=assignment,
                status=ProgressReportStatus.SUBMITTED,
            )
            ProjectProgressRevision.objects.create(
                report=report,
                revision_number=1,
                completed_activities=data["completed_activities"].strip(),
                challenges=data.get("challenges", "").strip(),
                next_steps=data.get("next_steps", "").strip(),
                submitted_by=actor,
            )
    except IntegrityError as exc:
        raise ValidationError("A progress report already exists for this milestone.") from exc
    return report


@transaction.atomic
def resubmit_progress_report(*, report_id, actor, data):
    report = ProjectProgressReport.objects.select_for_update().select_related(
        "student_enrollment",
        "milestone__session",
    ).get(pk=report_id)
    if report.student_enrollment.user_id != actor.id:
        raise ValidationError("You can only revise your own progress reports.")
    if report.status != ProgressReportStatus.REVISION_REQUESTED:
        raise ValidationError("This progress report is not awaiting a revision.")
    if report.milestone.session.status != AcademicSessionStatus.ACTIVE:
        raise ValidationError("This academic session is no longer accepting progress reports.")
    if not report.milestone.is_active:
        raise ValidationError("This project milestone is no longer accepting revisions.")

    assignment = _current_assignment(report.student_enrollment)
    if assignment is None:
        raise ValidationError("A current supervisor assignment is required to resubmit this report.")

    next_number = (report.revisions.order_by("-revision_number").values_list("revision_number", flat=True).first() or 0) + 1
    ProjectProgressRevision.objects.create(
        report=report,
        revision_number=next_number,
        completed_activities=data["completed_activities"].strip(),
        challenges=data.get("challenges", "").strip(),
        next_steps=data.get("next_steps", "").strip(),
        submitted_by=actor,
    )
    report.supervisor_assignment = assignment
    report.status = ProgressReportStatus.SUBMITTED
    report.submitted_at = timezone.now()
    report.reviewed_at = None
    report.save(
        update_fields=[
            "supervisor_assignment",
            "status",
            "submitted_at",
            "reviewed_at",
            "updated_at",
        ]
    )
    return report


@transaction.atomic
def review_progress_report(*, report_id, actor, decision, assessment, feedback=""):
    report = ProjectProgressReport.objects.select_for_update().select_related(
        "student_enrollment",
        "milestone",
    ).get(pk=report_id)
    if report.status != ProgressReportStatus.SUBMITTED:
        raise ValidationError("Only submitted progress reports can be reviewed.")

    assignment = _current_assignment(report.student_enrollment, actor=actor)
    if assignment is None:
        raise ValidationError("Only the student's currently assigned supervisor can review this report.")

    revision = report.revisions.order_by("-revision_number").first()
    if revision is None:
        raise ValidationError("The progress report could not be found.")

    from .models import ProjectProgressReview, ProgressReviewDecision

    ProjectProgressReview.objects.create(
        report=report,
        revision=revision,
        supervisor_assignment=assignment,
        reviewer=actor,
        decision=decision,
        assessment=assessment,
        feedback=feedback.strip(),
    )
    report.status = (
        ProgressReportStatus.REVISION_REQUESTED
        if decision == ProgressReviewDecision.REQUEST_REVISION
        else ProgressReportStatus.REVIEWED
    )
    report.reviewed_at = timezone.now()
    report.save(update_fields=["status", "reviewed_at", "updated_at"])
    return report
