import re

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone

from apps.accounts.models import Role, RoleCode, UserRole

from .models import (
    AcademicSession,
    AcademicSessionStatus,
    LecturerProfile,
    StudentEnrollment,
    StudentRosterRecord,
    StudentVerificationStatus,
    SupervisorAssignment,
    VerificationMethod,
    normalise_matric_number,
    normalise_person_name,
)

User = get_user_model()


def activate_academic_session(session_id, actor):
    with transaction.atomic():
        session = AcademicSession.objects.select_for_update().get(pk=session_id)
        active_session = (
            AcademicSession.objects.select_for_update()
            .filter(status=AcademicSessionStatus.ACTIVE)
            .exclude(pk=session.pk)
            .first()
        )
        if active_session:
            raise ValidationError(
                f"Close the active session ({active_session.name}) before activating another session."
            )
        if session.status != AcademicSessionStatus.PLANNED:
            raise ValidationError("Only a planned academic session can be activated.")
        session.status = AcademicSessionStatus.ACTIVE
        session.updated_by = actor
        try:
            with transaction.atomic():
                session.save(update_fields=["status", "updated_by", "updated_at"])
        except IntegrityError as exc:
            raise ValidationError("Another academic session was activated concurrently. Refresh and try again.") from exc
        return session


def close_academic_session(session_id, actor):
    with transaction.atomic():
        session = AcademicSession.objects.select_for_update().get(pk=session_id)
        if session.status != AcademicSessionStatus.ACTIVE:
            raise ValidationError("Only the active academic session can be closed.")
        session.status = AcademicSessionStatus.CLOSED
        session.updated_by = actor
        session.save(update_fields=["status", "updated_by", "updated_at"])
        return session


def normalise_email(value):
    return str(value or "").strip().casefold()


def normalise_phone(value):
    return re.sub(r"[\s().-]", "", str(value or "")).casefold()


def roster_registration_mismatches(
    roster_record,
    *,
    email,
    first_name,
    last_name,
    other_names="",
    phone="",
):
    if roster_record is None:
        return ["No matching matriculation number was found in the active session's departmental register."]

    mismatches = []
    if not roster_record.is_eligible:
        mismatches.append("The departmental record is not marked as eligible for final-year project registration.")
    if normalise_person_name(roster_record.first_name) != normalise_person_name(first_name):
        mismatches.append("First name does not match the departmental record.")
    if normalise_person_name(roster_record.last_name) != normalise_person_name(last_name):
        mismatches.append("Last name does not match the departmental record.")
    if roster_record.other_names and normalise_person_name(roster_record.other_names) != normalise_person_name(other_names):
        mismatches.append("Other names do not match the departmental record.")
    if roster_record.email and normalise_email(roster_record.email) != normalise_email(email):
        mismatches.append("Email address does not match the departmental record.")
    if roster_record.phone and normalise_phone(roster_record.phone) != normalise_phone(phone):
        mismatches.append("Phone number does not match the departmental record.")
    return mismatches


@transaction.atomic
def register_student(*, email, password, first_name, last_name, other_names, matric_number, phone=""):
    active_session = AcademicSession.objects.select_for_update().filter(
        status=AcademicSessionStatus.ACTIVE
    ).first()
    if active_session is None:
        raise ValidationError("Student registration is unavailable because there is no active academic session.")

    normalized_matric = normalise_matric_number(matric_number)
    if StudentEnrollment.objects.filter(
        session=active_session,
        matric_number=normalized_matric,
    ).exists():
        raise ValidationError("A registration already exists for this matriculation number in the active session.")

    roster_record = StudentRosterRecord.objects.filter(
        session=active_session,
        matric_number=normalized_matric,
    ).first()

    verification_mismatches = roster_registration_mismatches(
        roster_record,
        email=email,
        first_name=first_name,
        last_name=last_name,
        other_names=other_names,
        phone=phone,
    )
    verification_status = StudentVerificationStatus.PENDING_REVIEW
    verification_method = ""
    verified_at = None
    if not verification_mismatches:
        verification_status = StudentVerificationStatus.AUTO_VERIFIED
        verification_method = VerificationMethod.AUTOMATIC
        verified_at = timezone.now()

    try:
        with transaction.atomic():
            user = User.objects.create_user(
                email=email,
                password=password,
                first_name=first_name.strip(),
                last_name=last_name.strip(),
                is_active=True,
            )
            student_role = Role.objects.get(code=RoleCode.STUDENT)
            UserRole.objects.create(user=user, role=student_role)
            enrollment = StudentEnrollment.objects.create(
                user=user,
                session=active_session,
                roster_record=roster_record,
                matric_number=normalized_matric,
                other_names=other_names.strip(),
                phone=phone.strip(),
                verification_notes=" ".join(verification_mismatches),
                verification_status=verification_status,
                verification_method=verification_method,
                verified_at=verified_at,
            )
    except IntegrityError as exc:
        raise ValidationError("The email address or matriculation number is already registered.") from exc
    from apps.projects.lifecycle import coordinators, notify
    notify([user.pk], "registration", "Your project registration has been received.")
    if verification_status == StudentVerificationStatus.PENDING_REVIEW:
        notify(coordinators(), "registration", "A student registration requires manual review.")
    return user, enrollment


@transaction.atomic
def review_student_enrollment(*, enrollment_id, actor, decision, notes=""):
    enrollment = StudentEnrollment.objects.select_for_update().select_related("user").get(
        pk=enrollment_id
    )
    if enrollment.verification_status != StudentVerificationStatus.PENDING_REVIEW:
        raise ValidationError("Only registrations pending manual review can be reviewed.")

    if enrollment.roster_record is None:
        roster_record = StudentRosterRecord.objects.filter(
            session=enrollment.session,
            matric_number=enrollment.matric_number,
        ).first()
        if roster_record and not roster_record.enrollments.exclude(pk=enrollment.pk).exists():
            enrollment.roster_record = roster_record

    if decision == "approve":
        enrollment.verification_status = StudentVerificationStatus.MANUALLY_APPROVED
        enrollment.verification_method = VerificationMethod.MANUAL
        enrollment.verified_at = timezone.now()
    elif decision == "reject":
        enrollment.verification_status = StudentVerificationStatus.REJECTED
        enrollment.verification_method = VerificationMethod.MANUAL
        enrollment.verified_at = None
    else:
        raise ValidationError("Decision must be either 'approve' or 'reject'.")

    enrollment.reviewed_by = actor
    enrollment.reviewed_at = timezone.now()
    enrollment.review_notes = notes.strip()
    enrollment.save(
        update_fields=[
            "verification_status",
            "verification_method",
            "roster_record",
            "verified_at",
            "reviewed_by",
            "reviewed_at",
            "review_notes",
        ]
    )
    from apps.projects.lifecycle import notify
    notify([enrollment.user_id], "registration", "Your project registration has been reviewed.")
    return enrollment


@transaction.atomic
def create_lecturer_account(*, actor, email, password, first_name, last_name, staff_number="", designation="", phone="", office="", is_active=True):
    try:
        with transaction.atomic():
            user = User.objects.create_user(
                email=email,
                password=password,
                first_name=first_name.strip(),
                last_name=last_name.strip(),
                is_active=True,
            )
            lecturer_role = Role.objects.get(code=RoleCode.LECTURER)
            UserRole.objects.create(user=user, role=lecturer_role, assigned_by=actor)
            profile = LecturerProfile.objects.create(
                user=user,
                staff_number=staff_number or None,
                designation=designation,
                phone=phone,
                office=office,
                is_active=is_active,
                created_by=actor,
            )
    except IntegrityError as exc:
        raise ValidationError("The lecturer email address or staff number is already in use.") from exc
    return profile


@transaction.atomic
def assign_supervisor(*, enrollment_id, lecturer_id, actor):
    enrollment = StudentEnrollment.objects.get(pk=enrollment_id)
    session = AcademicSession.objects.select_for_update().get(pk=enrollment.session_id)
    enrollment = StudentEnrollment.objects.select_for_update().get(pk=enrollment_id)
    lecturer = LecturerProfile.objects.select_for_update().get(pk=lecturer_id)

    from apps.projects.models import ProjectCompletion

    reallocation_required = ProjectCompletion.objects.filter(
        enrollment=enrollment,
        status__in=["panel_reallocation_required", "scheduled"],
        events__action="panel_reallocation_required",
    ).exclude(scores__round=F("score_round")).exists()
    if session.status != AcademicSessionStatus.ACTIVE and not (
        session.status == AcademicSessionStatus.CLOSED and reallocation_required
    ):
        raise ValidationError("Supervisors can only be assigned during the active academic session.")
    if not enrollment.is_verified:
        raise ValidationError("A supervisor can only be assigned to a verified student.")
    if not lecturer.is_active or not lecturer.user.is_active:
        raise ValidationError("The selected lecturer is not active for supervision.")
    if (
        not lecturer.user.has_role(RoleCode.LECTURER)
        or lecturer.user.has_role(RoleCode.STUDENT)
        or StudentEnrollment.objects.filter(user=lecturer.user).exists()
    ):
        raise ValidationError("The selected account does not have the Lecturer role.")
    if SupervisorAssignment.objects.filter(
        student_enrollment=enrollment,
        is_current=True,
    ).exists():
        raise ValidationError("This student already has a supervisor. Use the reassignment action.")

    try:
        assignment = SupervisorAssignment.objects.create(
            student_enrollment=enrollment,
            lecturer=lecturer,
            assigned_by=actor,
        )
        from apps.projects.lifecycle import notify
        notify([enrollment.user_id, lecturer.user_id], "supervision", "A project supervisor assignment has been created.")
        return assignment
    except IntegrityError as exc:
        raise ValidationError("A current supervisor assignment already exists for this student.") from exc


@transaction.atomic
def reassign_supervisor(*, assignment_id, lecturer_id, actor, reason):
    reason = reason.strip()
    if not reason:
        raise ValidationError({"reason": "A reassignment reason is required."})

    initial = SupervisorAssignment.objects.filter(pk=assignment_id, is_current=True).values_list("student_enrollment__session_id", flat=True).first()
    if initial is None:
        raise ValidationError("Only a current supervisor assignment can be reassigned.")
    session = AcademicSession.objects.select_for_update().get(pk=initial)
    current_assignment = (
        SupervisorAssignment.objects.select_for_update()
        .select_related("student_enrollment")
        .filter(pk=assignment_id, is_current=True)
        .first()
    )
    if current_assignment is None:
        raise ValidationError("Only a current supervisor assignment can be reassigned.")
    new_lecturer = LecturerProfile.objects.select_for_update().get(pk=lecturer_id)
    from apps.projects.models import ProjectCompletion

    reallocation_required = ProjectCompletion.objects.filter(
        enrollment=current_assignment.student_enrollment,
        status__in=["panel_reallocation_required", "scheduled"],
        events__action="panel_reallocation_required",
    ).exclude(scores__round=F("score_round")).exists()
    if session.status != AcademicSessionStatus.ACTIVE and not (
        session.status == AcademicSessionStatus.CLOSED and reallocation_required
    ):
        raise ValidationError("Supervisor assignments can only be changed during the active academic session.")
    if current_assignment.lecturer_id == new_lecturer.id:
        raise ValidationError("The new supervisor must be different from the current supervisor.")
    if not new_lecturer.is_active or not new_lecturer.user.is_active:
        raise ValidationError("The selected lecturer is not active for supervision.")
    if (
        not new_lecturer.user.has_role(RoleCode.LECTURER)
        or new_lecturer.user.has_role(RoleCode.STUDENT)
        or StudentEnrollment.objects.filter(user=new_lecturer.user).exists()
    ):
        raise ValidationError("The selected account does not have the Lecturer role.")

    from apps.projects.models import ProjectCompletion
    if ProjectCompletion.objects.filter(enrollment=current_assignment.student_enrollment, panel__members=new_lecturer).exists():
        raise ValidationError("This lecturer is on the student's examination panel. Reallocate the panel before changing supervisors.")

    now = timezone.now()
    current_assignment.is_current = False
    current_assignment.ended_at = now
    current_assignment.ended_by = actor
    current_assignment.save(update_fields=["is_current", "ended_at", "ended_by"])

    try:
        new_assignment = SupervisorAssignment.objects.create(
            student_enrollment=current_assignment.student_enrollment,
            lecturer=new_lecturer,
            assigned_by=actor,
            assigned_at=now,
            reassignment_reason=reason,
        )
        from apps.projects.models import ProjectTopic

        ProjectTopic.objects.filter(
            student_enrollment=current_assignment.student_enrollment,
            is_current=True,
        ).update(supervisor_assignment=new_assignment, updated_at=now)
        from apps.projects.lifecycle import notify
        notify([current_assignment.student_enrollment.user_id, new_lecturer.user_id, current_assignment.lecturer.user_id], "supervision", "A project supervisor assignment has changed.")
        return new_assignment
    except IntegrityError as exc:
        raise ValidationError("The supervisor assignment changed concurrently. Refresh and try again.") from exc
