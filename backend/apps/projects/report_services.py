from pathlib import Path

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.academics.models import (
    AcademicSession,
    AcademicSessionStatus,
    StudentEnrollment,
    StudentVerificationStatus,
    SupervisorAssignment,
)

from .models import (
    ProjectCompletion,
    ProjectReportRevision,
    ProjectReportReview,
    ProjectReportSection,
    ProjectReportSubmission,
    ReportReviewDecision,
    ReportSubmissionStatus,
)
from .report_files import (
    ReportStorageError,
    new_report_object_path,
    read_report_document,
    remove_report_document,
    upload_report_document,
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


def _validate_section_is_unlocked(*, section, enrollment):
    if ProjectCompletion.objects.filter(enrollment=enrollment).exclude(status__in=["revision_requested", "clearance_denied"]).exists():
        raise ValidationError("Report sections are locked after final project submission.")
    previous_sections = ProjectReportSection.objects.filter(
        session=section.session,
        is_active=True,
        sequence__lt=section.sequence,
    ).order_by("sequence")
    for previous in previous_sections:
        previous_submission = ProjectReportSubmission.objects.filter(
            section=previous,
            student_enrollment=enrollment,
        ).first()
        if previous_submission is None:
            if previous.is_required:
                raise ValidationError(
                    f"Complete and obtain approval for '{previous.title}' before submitting this section."
                )
            continue
        if previous_submission.status != ReportSubmissionStatus.APPROVED:
            raise ValidationError(
                f"Your '{previous.title}' section must be approved before you can submit this section."
            )


def _upload_revision_file(*, uploaded_file, section, enrollment):
    content, metadata = read_report_document(uploaded_file)
    extension = Path(metadata["original_filename"]).suffix.lower()
    object_path = new_report_object_path(
        session_id=section.session_id,
        enrollment_id=enrollment.pk,
        section_id=section.pk,
        extension=extension,
    )
    try:
        upload_report_document(
            object_path=object_path,
            content=content,
            content_type=metadata["content_type"],
        )
    except ReportStorageError as exc:
        remove_report_document(object_path)
        raise ValidationError(
            "Document upload is temporarily unavailable. Please try again later."
        ) from exc
    return object_path, metadata


def submit_report_section(*, actor, section_id, uploaded_file, submission_note=""):
    section = ProjectReportSection.objects.select_related("session").filter(
        pk=section_id
    ).first()
    if section is None:
        raise ValidationError("The selected report section could not be found.")
    if not section.is_active:
        raise ValidationError("This report section is not currently accepting submissions.")
    if section.session.status != AcademicSessionStatus.ACTIVE:
        raise ValidationError("Report sections can only be submitted during an active academic session.")

    enrollment = StudentEnrollment.objects.filter(
        user=actor,
        session=section.session,
        verification_status__in=VERIFIED_STATUSES,
    ).first()
    if enrollment is None:
        raise ValidationError("A verified student registration is required to submit this report section.")

    assignment = _current_assignment(enrollment)
    if assignment is None:
        raise ValidationError("A supervisor must be assigned before submitting a report section.")

    _validate_section_is_unlocked(section=section, enrollment=enrollment)
    if ProjectReportSubmission.objects.filter(
        section=section,
        student_enrollment=enrollment,
    ).exists():
        raise ValidationError("A submission already exists for this section. You can resubmit after your supervisor requests a revision.")

    object_path, metadata = _upload_revision_file(
        uploaded_file=uploaded_file,
        section=section,
        enrollment=enrollment,
    )
    try:
        with transaction.atomic():
            AcademicSession.objects.select_for_update().get(pk=section.session_id)
            locked_section = ProjectReportSection.objects.select_for_update().select_related(
                "session"
            ).get(pk=section.pk)
            locked_enrollment = StudentEnrollment.objects.select_for_update().get(pk=enrollment.pk)
            if not locked_section.is_active or locked_section.session.status != AcademicSessionStatus.ACTIVE:
                raise ValidationError("This report section is no longer accepting submissions.")
            if locked_enrollment.verification_status not in VERIFIED_STATUSES:
                raise ValidationError("A verified student registration is required to submit this report section.")
            current_assignment = _current_assignment(locked_enrollment)
            if current_assignment is None:
                raise ValidationError("A supervisor must be assigned before submitting a report section.")
            _validate_section_is_unlocked(section=locked_section, enrollment=locked_enrollment)
            if ProjectReportSubmission.objects.filter(
                section=locked_section,
                student_enrollment=locked_enrollment,
            ).exists():
                raise ValidationError("A submission already exists for this section. You can resubmit after your supervisor requests a revision.")
            submission = ProjectReportSubmission.objects.create(
                section=locked_section,
                student_enrollment=locked_enrollment,
                supervisor_assignment=current_assignment,
                status=ReportSubmissionStatus.SUBMITTED,
            )
            ProjectReportRevision.objects.create(
                submission=submission,
                revision_number=1,
                storage_path=object_path,
                original_filename=metadata["original_filename"],
                file_size=metadata["file_size"],
                content_type=metadata["content_type"],
                submission_note=submission_note.strip(),
                uploaded_by=actor,
            )
            from .lifecycle import notify
            notify([current_assignment.lecturer.user_id], "reports", "A report section is awaiting your review.")
    except IntegrityError as exc:
        remove_report_document(object_path)
        raise ValidationError("A submission already exists for this report section.") from exc
    except Exception:
        remove_report_document(object_path)
        raise

    return submission


def resubmit_report_section(*, submission_id, actor, uploaded_file, submission_note=""):
    submission = ProjectReportSubmission.objects.select_related(
        "student_enrollment",
        "section__session",
    ).filter(pk=submission_id).first()
    if submission is None:
        raise ValidationError("The report submission could not be found.")
    if not submission.student_enrollment.is_verified:
        raise ValidationError("A verified student registration is required to revise this report section.")
    if submission.student_enrollment.user_id != actor.id:
        raise ValidationError("You can only revise your own report submissions.")
    if submission.status != ReportSubmissionStatus.REVISION_REQUESTED:
        raise ValidationError("This report section is not awaiting a revision.")
    if submission.section.session.status != AcademicSessionStatus.ACTIVE:
        raise ValidationError("This academic session is no longer accepting report submissions.")
    if not submission.section.is_active:
        raise ValidationError("This report section is not currently accepting revisions.")

    assignment = _current_assignment(submission.student_enrollment)
    if assignment is None:
        raise ValidationError("A current supervisor assignment is required to resubmit this section.")
    _validate_section_is_unlocked(
        section=submission.section,
        enrollment=submission.student_enrollment,
    )

    object_path, metadata = _upload_revision_file(
        uploaded_file=uploaded_file,
        section=submission.section,
        enrollment=submission.student_enrollment,
    )
    try:
        with transaction.atomic():
            AcademicSession.objects.select_for_update().get(pk=submission.section.session_id)
            locked_submission = ProjectReportSubmission.objects.select_for_update().select_related(
                "student_enrollment",
                "section__session",
            ).get(pk=submission.pk)
            if locked_submission.student_enrollment.user_id != actor.id:
                raise ValidationError("You can only revise your own report submissions.")
            if not locked_submission.student_enrollment.is_verified:
                raise ValidationError("A verified student registration is required to revise this report section.")
            if locked_submission.status != ReportSubmissionStatus.REVISION_REQUESTED:
                raise ValidationError("This report section is no longer awaiting a revision.")
            if (
                locked_submission.section.session.status != AcademicSessionStatus.ACTIVE
                or not locked_submission.section.is_active
            ):
                raise ValidationError("This report section is no longer accepting revisions.")
            current_assignment = _current_assignment(locked_submission.student_enrollment)
            if current_assignment is None:
                raise ValidationError("A current supervisor assignment is required to resubmit this section.")
            _validate_section_is_unlocked(
                section=locked_submission.section,
                enrollment=locked_submission.student_enrollment,
            )
            next_number = (
                locked_submission.revisions.order_by("-revision_number").values_list(
                    "revision_number",
                    flat=True,
                ).first() or 0
            ) + 1
            ProjectReportRevision.objects.create(
                submission=locked_submission,
                revision_number=next_number,
                storage_path=object_path,
                original_filename=metadata["original_filename"],
                file_size=metadata["file_size"],
                content_type=metadata["content_type"],
                submission_note=submission_note.strip(),
                uploaded_by=actor,
            )
            locked_submission.supervisor_assignment = current_assignment
            locked_submission.status = ReportSubmissionStatus.SUBMITTED
            locked_submission.submitted_at = timezone.now()
            locked_submission.reviewed_at = None
            locked_submission.save(
                update_fields=[
                    "supervisor_assignment",
                    "status",
                    "submitted_at",
                    "reviewed_at",
                    "updated_at",
                ]
            )
            from .lifecycle import notify
            notify([current_assignment.lecturer.user_id], "reports", "A revised report section is awaiting your review.")
    except Exception:
        remove_report_document(object_path)
        raise

    return locked_submission


def review_report_section(*, submission_id, actor, decision, feedback="", annotation=None):
    uploaded_paths = []
    try:
        with transaction.atomic():
            return _review_report_section(submission_id, actor, decision, feedback, annotation, uploaded_paths)
    except Exception:
        for path in uploaded_paths:
            remove_report_document(path)
        raise


def _review_report_section(submission_id, actor, decision, feedback, annotation, uploaded_paths):
    session_id = ProjectReportSubmission.objects.filter(pk=submission_id).values_list("section__session_id", flat=True).first()
    if session_id is None:
        raise ValidationError("The report submission could not be found.")
    AcademicSession.objects.select_for_update().get(pk=session_id)
    submission = ProjectReportSubmission.objects.select_for_update().select_related(
        "student_enrollment",
        "section",
    ).filter(pk=submission_id).first()
    if submission is None:
        raise ValidationError("The report submission could not be found.")
    if submission.section.session.status != AcademicSessionStatus.ACTIVE:
        raise ValidationError("This academic session is closed to report reviews.")
    if decision not in ReportReviewDecision.values:
        raise ValidationError("Select a valid review decision.")
    if submission.status != ReportSubmissionStatus.SUBMITTED:
        raise ValidationError("Only submitted report sections can be reviewed.")

    assignment = _current_assignment(submission.student_enrollment, actor=actor)
    if assignment is None:
        raise ValidationError("Only the student's currently assigned supervisor can review this section.")
    if decision == ReportReviewDecision.REQUEST_REVISION and not feedback.strip():
        raise ValidationError("Provide feedback explaining the changes required.")

    revision = submission.revisions.order_by("-revision_number").first()
    if revision is None:
        raise ValidationError("The submitted document could not be found.")

    annotation_values = {}
    if annotation is not None:
        from .lifecycle import upload_document
        annotation_path, metadata = upload_document(annotation, submission.student_enrollment, "annotations")
        uploaded_paths.append(annotation_path)
        annotation_values = {"annotation_path": annotation_path, "annotation_filename": metadata["original_filename"]}
    ProjectReportReview.objects.create(
        submission=submission,
        revision=revision,
        supervisor_assignment=assignment,
        reviewer=actor,
        decision=decision,
        feedback=feedback.strip(),
        **annotation_values,
    )
    submission.status = (
        ReportSubmissionStatus.APPROVED
        if decision == ReportReviewDecision.APPROVE
        else ReportSubmissionStatus.REVISION_REQUESTED
    )
    submission.reviewed_at = timezone.now()
    submission.save(update_fields=["status", "reviewed_at", "updated_at"])
    from .lifecycle import notify
    notify([submission.student_enrollment.user_id], "reports", "Your supervisor has reviewed a report section.")
    return submission
