"""Academic completion workflows. All writes are explicit, audited transitions."""
import logging
import os
from collections.abc import Mapping
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.accounts.models import RoleCode, User
from apps.academics.models import AcademicSession, LecturerProfile, StudentEnrollment, SupervisorAssignment
from .assessment_math import aggregate_marks
from .models import (
    AssessmentScheme, CompletionEvent, DeadlineExtension, DefencePanel, ExaminerScore,
    FinalReportVersion, NotificationPreference, ProjectCompletion, ProjectDeadline,
    ProjectNotification, ProjectReportSection, ProjectReportSubmission, ProjectTopic, ResultAppeal,
)
from .report_services import _current_assignment, VERIFIED_STATUSES
from .report_files import (
    ReportStorageError, new_report_object_path, read_report_document, remove_report_document,
    upload_report_document,
)

CATEGORIES = ("registration", "supervision", "topics", "reports", "deadlines", "defence", "results", "appeals")
DEADLINE_KINDS = ("topic", "final", "defence")
POST_PUBLICATION_ACTIONS = {"appeal", "review_appeal", "accept_appeal", "reject_appeal", "score", "approve_result", "return_result", "publish"}
logger = logging.getLogger(__name__)


def coordinator(user):
    return user.has_role(RoleCode.PROJECT_COORDINATOR)


def lecturer_account(user):
    return (
        user.has_role(RoleCode.LECTURER)
        and not user.has_role(RoleCode.STUDENT)
        and not StudentEnrollment.objects.filter(user=user).exists()
    )


def supervisor(user, enrollment):
    return lecturer_account(user) and _current_assignment(enrollment, actor=user) is not None


def examiner(user, project):
    if (
        not project.panel_id
        or not lecturer_account(user)
    ):
        return None
    has_supervised_project = SupervisorAssignment.objects.filter(
        student_enrollment=project.enrollment,
        lecturer__user=user,
    ).exists()
    if has_supervised_project:
        return None
    return project.panel.members.filter(
        user=user,
        is_active=True,
        user__is_active=True,
    ).first()


def require(condition, message="You cannot perform this action."):
    if not condition:
        raise PermissionDenied(message)


def check(condition, message):
    if not condition:
        raise ValidationError({"detail": message})


def text(data, key, maximum=5000, required=True):
    return serializers.CharField(max_length=maximum, allow_blank=not required).run_validation(data.get(key, ""))


def uid(value):
    return serializers.UUIDField().run_validation(value)


def date(value):
    return serializers.DateField().run_validation(value)


def get_row(model, value, **filters):
    obj = model.objects.filter(pk=uid(value), **filters).first()
    check(obj is not None, "The selected record is unavailable.")
    return obj


def notify(users, category, message):
    """Persist in-app notifications; email is opt-in and best-effort after commit."""
    for user in User.objects.filter(pk__in=set(users), is_active=True):
        prefs = NotificationPreference.objects.filter(user=user).first()
        preference = (prefs.categories if prefs else {}).get(category, {})
        if preference.get("in_app", True):
            ProjectNotification.objects.create(recipient=user, category=category, message=message)
        if preference.get("email", False) and os.environ.get("PROJFLOW_EMAIL_ENABLED", "").lower() == "true":
            def deliver(to=user.email):
                try:
                    send_mail("ProjFlow academic update", "A new academic update is available. Sign in to ProjFlow to review it.", settings.DEFAULT_FROM_EMAIL, [to])
                except Exception:
                    logger.warning("ProjFlow notification email delivery failed.")
            transaction.on_commit(deliver)


def coordinators():
    return User.objects.filter(role_assignments__role__code=RoleCode.PROJECT_COORDINATOR).values_list("pk", flat=True)


def event(project, user, action, note="", data=None, category="defence"):
    CompletionEvent.objects.create(project=project, actor=user, action=action, note=note, data=data or {})
    assignment = _current_assignment(project.enrollment)
    users = {project.enrollment.user_id, *coordinators()}
    if assignment:
        users.add(assignment.lecturer.user_id)
    if project.panel_id:
        users.update(project.panel.members.values_list("user_id", flat=True))
    users.discard(user.pk)
    notify(users, category, "A project workflow has been updated. Open Final project and defence for details.")


def base_deadline(session, kind):
    if kind.startswith("section:"):
        section = get_row(ProjectReportSection, kind.split(":", 1)[1], session=session, is_active=True)
        return section.due_date
    check(kind in DEADLINE_KINDS, "Invalid deadline category.")
    return ProjectDeadline.objects.filter(session=session, kind=kind).values_list("due_date", flat=True).first()


def effective_deadline(enrollment, kind, original=None):
    original = original or base_deadline(enrollment.session, kind)
    approved = DeadlineExtension.objects.filter(enrollment=enrollment, kind=kind, status="approved").order_by("-requested_date").first()
    dates = [value for value in (original, approved.requested_date if approved else None) if value]
    return max(dates) if dates else None


def normalize_components(raw):
    check(isinstance(raw, list) and 1 <= len(raw) <= 30, "Enter between 1 and 30 assessment components.")
    result = []
    for item in raw:
        check(isinstance(item, dict), "Invalid assessment component.")
        label = text(item, "name", 150)
        maximum = serializers.IntegerField(min_value=1, max_value=100).run_validation(item.get("maximum"))
        check(label.casefold() not in {c["name"].casefold() for c in result}, "Component names must be distinct.")
        result.append({"name": label, "maximum": maximum})
    check(sum(c["maximum"] for c in result) == 100, "Component maxima must total exactly 100.")
    return result


def normalize_marks(raw, components):
    check(isinstance(raw, list) and len(raw) == len(components), "Enter a mark for every assessment component.")
    result = []
    for mark, component in zip(raw, components):
        try:
            score = Decimal(str(mark))
            valid = score.is_finite() and 0 <= score <= component["maximum"] and score == score.quantize(Decimal("0.01"))
        except (InvalidOperation, ValueError):
            valid = False
        check(valid, f"Invalid mark for {component['name']}; enter 0–{component['maximum']} with up to two decimal places.")
        result.append(str(score.quantize(Decimal("0.01"))))
    return result


def latest_scores(project):
    scores = {}
    for score in project.scores.filter(round__lte=project.score_round).order_by("round", "submitted_at"):
        scores[score.examiner_id] = score
    return scores


def result_for(project):
    if not project.panel_id or not project.components:
        return None
    members = set(project.panel.members.values_list("pk", flat=True))
    scores = {score.examiner_id: score for score in project.scores.filter(round=project.score_round)}
    if not members or not members.issubset(scores):
        return None
    return aggregate_marks(project.components, [scores[member].marks for member in members])


def validate_panel(project):
    assignment = SupervisorAssignment.objects.filter(student_enrollment=project.enrollment, is_current=True).first()
    check(assignment is not None and project.panel_id, "A current supervisor and examination panel are required.")
    previous_supervisor_ids = SupervisorAssignment.objects.filter(
        student_enrollment=project.enrollment
    ).values("lecturer_id")
    check(
        not project.panel.members.filter(pk__in=previous_supervisor_ids).exists(),
        "A current or former supervisor cannot examine this project.",
    )
    check(not project.panel.members.filter(Q(is_active=False) | Q(user__is_active=False)).exists(), "The panel contains an inactive examiner. Contact the Coordinator.")
    check(
        not project.panel.members.filter(
            user__role_assignments__role__code=RoleCode.STUDENT
        ).exists(),
        "Student accounts cannot serve as examiners.",
    )
    check(
        not project.panel.members.filter(
            user__student_enrollments__isnull=False
        ).exists(),
        "Accounts with student enrollments cannot serve as examiners.",
    )
    check(project.panel.members.exists(), "The selected examination panel must contain an active examiner.")
    check(project.panel.members.count() == project.panel.members.filter(user__role_assignments__role__code=RoleCode.LECTURER).distinct().count(), "All panel members must retain the Lecturer role.")


def independent_coordinator(user, project):
    """A result approver must not have examined or scored the same project."""
    if not coordinator(user):
        return False
    if project.panel_id and project.panel.members.filter(user=user).exists():
        return False
    return not project.scores.filter(examiner__user=user).exists()


def upload_document(uploaded_file, enrollment, namespace):
    content, metadata = read_report_document(uploaded_file)
    path = new_report_object_path(session_id=enrollment.session_id, enrollment_id=enrollment.pk, section_id=namespace, extension=Path(metadata["original_filename"]).suffix.lower())
    try:
        upload_report_document(object_path=path, content=content, content_type=metadata["content_type"])
    except ReportStorageError as exc:
        remove_report_document(path)
        raise ValidationError({"detail": "Document upload is temporarily unavailable. Please try again."}) from exc
    return path, metadata


def project_data(project, user):
    own = project.enrollment.user_id == user.pk and user.has_role(RoleCode.STUDENT)
    coord = coordinator(user)
    sup = supervisor(user, project.enrollment)
    member = examiner(user, project)
    active = project.enrollment.session.status == "active"
    state = project.status
    actions = []
    reopened_for_panel_integrity = project.events.filter(
        action="panel_reallocation_required"
    ).exists()
    if active or project.published_at or reopened_for_panel_integrity:
        if active and own and state in ("revision_requested", "clearance_denied"):
            actions.append("submit")
        if sup and state == "submitted":
            actions.extend(["recommend", "decline"])
        if coord and state == "recommended":
            actions.extend(["clear", "deny_clearance"])
        if coord and state in ("cleared", "scheduled", "panel_reallocation_required") and not project.scores.filter(round=project.score_round).exists():
            actions.append("schedule")
        if member and state in ("scheduled", "scoring", "correction") and (project.defence_at and timezone.now() >= project.defence_at) and not project.scores.filter(examiner=member, round=project.score_round).exists():
            actions.append("score")
        if independent_coordinator(user, project) and state in ("scoring", "correction") and result_for(project):
            actions.extend(["approve_result", "return_result"])
        if independent_coordinator(user, project) and state == "approved":
            actions.extend(["publish", "return_result"])
        if own and state == "published" and project.published_at and timezone.now() <= project.published_at + timedelta(days=14) and not project.appeals.filter(status__in=["pending", "reviewed"]).exists():
            actions.append("appeal")
        if member and state == "published" and project.appeals.filter(status="pending").exists():
            actions.append("review_appeal")
        if independent_coordinator(user, project) and state == "published" and project.appeals.filter(status="reviewed").exists():
            actions.extend(["accept_appeal", "reject_appeal"])
    history = project.events.exclude(action="score").order_by("created_at")
    if not (coord or member):
        history = history.exclude(action__in=["review_appeal", "return_result", "approve_result"])
    shared = {
        "id": str(project.pk), "enrollment": str(project.enrollment_id),
        "student": project.enrollment.user.get_full_name(), "matric": project.enrollment.matric_number,
        "session": project.enrollment.session.name, "status": state, "actions": actions,
        "panel": str(project.panel_id) if project.panel_id else None,
        "panel_name": project.panel.name if project.panel_id else "",
        "defence_at": project.defence_at, "venue": project.venue,
        "components": project.components if (member or coord or sup) else [],
        "published_result": project.published_result, "published_at": None if state == "panel_reallocation_required" else project.published_at,
        "documents": [{"id": str(d.pk), "filename": d.original_filename, "version": d.version, "note": d.note, "created_at": d.created_at} for d in project.documents.order_by("version")] if (own or sup or member or coord) else [],
        "events": [{"action": e.action, "note": e.note, "created_at": e.created_at, "schedule": {"panel_name": e.data.get("panel_name", ""), "defence_at": e.data.get("defence_at"), "venue": e.data.get("venue", "")} if e.action == "schedule" else None} for e in history],
        "appeals": [{"id": str(a.pk), "complaint": a.complaint, "status": a.status, "panel_feedback": a.panel_feedback if (coord or member) else "", "decision_note": a.decision_note, "created_at": a.created_at} for a in project.appeals.order_by("created_at") if own or coord or member],
    }
    if coord:
        shared["draft_result"] = result_for(project)
        shared["score_count"] = project.scores.filter(round=project.score_round).count()
        shared["panel_size"] = project.panel.members.count() if project.panel_id else 0
    if member:
        previous = latest_scores(project).get(member.pk)
        shared["my_marks"] = (
            previous.marks
            if previous and (previous.round == project.score_round or state == "correction")
            else []
        )
    return shared


def visible_projects(user, session):
    queryset = ProjectCompletion.objects.filter(enrollment__session=session).select_related("enrollment__user", "enrollment__session", "panel")
    if coordinator(user):
        return queryset
    filters = Q(pk__in=[])
    if user.has_role(RoleCode.STUDENT):
        filters |= Q(enrollment__user=user)
    if lecturer_account(user):
        filters |= Q(enrollment__supervisor_assignments__is_current=True, enrollment__supervisor_assignments__lecturer__user=user, enrollment__supervisor_assignments__lecturer__is_active=True)
        supervised_projects = SupervisorAssignment.objects.filter(
            lecturer__user=user
        ).values("student_enrollment_id")
        filters |= Q(panel__members__user=user, panel__members__is_active=True) & ~Q(enrollment_id__in=supervised_projects)
    return queryset.filter(filters).distinct()


def session_data(user, session):
    coord = coordinator(user)
    enrollments = StudentEnrollment.objects.filter(session=session, verification_status__in=VERIFIED_STATUSES).select_related("user", "session")
    own = enrollments.filter(user=user).first() if user.has_role(RoleCode.STUDENT) else None
    assigned = enrollments.filter(supervisor_assignments__is_current=True, supervisor_assignments__lecturer__user=user, supervisor_assignments__lecturer__is_active=True) if lecturer_account(user) else enrollments.none()
    profile = LecturerProfile.objects.filter(user=user, is_active=True).first() if lecturer_account(user) else None
    deadlines = [{"kind": d.kind, "label": {"topic": "Project topic", "final": "Final project", "defence": "Defence"}[d.kind], "due_date": d.due_date} for d in ProjectDeadline.objects.filter(session=session, kind__in=DEADLINE_KINDS)]
    deadlines += [{"kind": f"section:{s.pk}", "label": s.title, "due_date": s.due_date} for s in ProjectReportSection.objects.filter(session=session, is_active=True, due_date__isnull=False)]
    if own:
        for item in deadlines:
            item["effective_date"] = effective_deadline(own, item["kind"], item["due_date"])
            item["overdue"] = item["effective_date"] < timezone.localdate()
            kind = item["kind"]
            if kind == "topic":
                item["completed"] = ProjectTopic.objects.filter(student_enrollment=own).exists()
            elif kind == "final":
                item["completed"] = ProjectCompletion.objects.filter(enrollment=own, documents__isnull=False).exists()
            elif kind == "defence":
                item["completed"] = ProjectCompletion.objects.filter(enrollment=own, status__in=["scoring", "correction", "approved", "published"]).exists()
            else:
                item["completed"] = ProjectReportSubmission.objects.filter(student_enrollment=own, section_id=kind.split(":", 1)[1]).exists()
            item["overdue"] = item["overdue"] and not item["completed"]
    extensions = DeadlineExtension.objects.filter(enrollment__session=session).select_related("enrollment__user")
    if not coord:
        extensions = extensions.filter(enrollment=own) if own else extensions.none()
    scheme = AssessmentScheme.objects.filter(session=session, lecturer=profile).first() if profile else None
    projects = list(visible_projects(user, session))
    required_sections = ProjectReportSection.objects.filter(session=session, is_active=True, is_required=True)
    required_count = required_sections.count()
    approved_count = ProjectReportSubmission.objects.filter(student_enrollment=own, section__in=required_sections, status="approved").count() if own else 0
    topic_ok = own and ProjectTopic.objects.filter(student_enrollment=own, status="approved", is_current=True).exists()
    can_submit = bool(own and session.status == "active" and _current_assignment(own) and required_count and required_count == approved_count and topic_ok and not ProjectReportSubmission.objects.filter(student_enrollment=own, section__is_active=True).exclude(status="approved").exists())
    progress_enrollments = enrollments if coord else (assigned | enrollments.filter(pk=own.pk) if own else assigned)
    progress = progress_register(progress_enrollments.distinct(), deadlines, required_count)
    return {
        "session": str(session.pk), "session_status": session.status, "coordinator": coord,
        "student": bool(own), "lecturer": bool(profile), "enrollment": str(own.pk) if own else None,
        "can_submit": can_submit, "required_count": required_count, "approved_count": approved_count,
        "topic_approved": bool(topic_ok), "supervisor_assigned": bool(own and _current_assignment(own)),
        "deadlines": deadlines, "sections": [{"kind": f"section:{section.pk}", "label": section.title} for section in ProjectReportSection.objects.filter(session=session, is_active=True)] if coord else [], "scheme": scheme.components if scheme else [],
        "assigned_count": assigned.count(),
        "extensions": [{"id": str(e.pk), "kind": e.kind, "label": next((d["label"] for d in deadlines if d["kind"] == e.kind), e.kind), "student": e.enrollment.user.get_full_name(), "matric": e.enrollment.matric_number, "original_due_date": e.original_due_date, "requested_date": e.requested_date, "justification": e.justification, "status": e.status, "decision_note": e.decision_note, "created_at": e.created_at} for e in extensions.order_by("-created_at")],
        "panels": [
            {
                "id": str(panel.pk),
                "name": panel.name,
                "members": [
                    {"id": str(member.pk), "name": member.user.get_full_name()}
                    for member in panel.members.select_related("user").all()
                ],
            }
            for panel in DefencePanel.objects.filter(session=session).prefetch_related("members__user")
            if panel.members.filter(is_active=True, user__is_active=True, user__role_assignments__role__code=RoleCode.LECTURER).exclude(user__role_assignments__role__code=RoleCode.STUDENT).exclude(user__student_enrollments__isnull=False).distinct().count() == panel.members.count() and panel.members.exists()
        ] if coord else [],
        "lecturers": [{"id": str(l.pk), "name": l.user.get_full_name()} for l in LecturerProfile.objects.filter(is_active=True, user__is_active=True, user__role_assignments__role__code=RoleCode.LECTURER).exclude(user__role_assignments__role__code=RoleCode.STUDENT).exclude(user__student_enrollments__isnull=False).select_related("user").distinct()] if coord else [],
        "projects": [project_data(p, user) for p in projects],
        "progress": progress,
        "summary": {"verified_students": enrollments.count() if coord else None, "final_submissions": len(projects), "cleared": sum(p.status in ["cleared", "scheduled", "panel_reallocation_required", "scoring", "correction", "approved", "published"] for p in projects), "published": sum(bool(p.published_at) for p in projects), "pending_extensions": extensions.filter(status="pending").count(), "overdue_students": sum(bool(p["overdue"]) for p in progress), "topics_approved": sum(p["topic_status"] == "approved" for p in progress)},
    }


def progress_register(enrollments, deadlines, required_count):
    """Metadata-only progress overview, restricted to the caller's students."""
    rows = list(enrollments)
    ids = [row.pk for row in rows]
    topics = {t.student_enrollment_id: t for t in ProjectTopic.objects.filter(student_enrollment_id__in=ids, is_current=True)}
    attempted_topics = set(ProjectTopic.objects.filter(student_enrollment_id__in=ids).values_list("student_enrollment_id", flat=True))
    reports = {}
    for report in ProjectReportSubmission.objects.filter(student_enrollment_id__in=ids, section__is_active=True).select_related("section"):
        reports.setdefault(report.student_enrollment_id, {})[f"section:{report.section_id}"] = report
    finals = {p.enrollment_id: p for p in ProjectCompletion.objects.filter(enrollment_id__in=ids)}
    assignments = {a.student_enrollment_id: a.lecturer.user.get_full_name() for a in SupervisorAssignment.objects.filter(student_enrollment_id__in=ids, is_current=True).select_related("lecturer__user")}
    extensions = {}
    for e in DeadlineExtension.objects.filter(enrollment_id__in=ids, status="approved").order_by("requested_date"):
        extensions[(e.enrollment_id, e.kind)] = e.requested_date
    result = []
    for row in rows:
        topic = topics.get(row.pk)
        sections = reports.get(row.pk, {})
        final = finals.get(row.pk)
        overdue = []
        for deadline in deadlines:
            kind = deadline["kind"]
            due = max(deadline["due_date"], extensions.get((row.pk, kind), deadline["due_date"]))
            completed = (row.pk in attempted_topics if kind == "topic" else bool(final) if kind == "final" else bool(final and final.status in ["scoring", "correction", "approved", "published"]) if kind == "defence" else kind in sections)
            if due < timezone.localdate() and not completed:
                overdue.append({"label": deadline["label"], "due_date": due})
        result.append({"id": str(row.pk), "name": row.user.get_full_name(), "matric": row.matric_number, "supervisor": assignments.get(row.pk, ""), "topic_status": topic.status if topic else "not_submitted", "sections_approved": sum(r.status == "approved" and r.section.is_required for r in sections.values()), "sections_required": required_count, "pending_reviews": sum(r.status == "submitted" for r in sections.values()), "final_status": final.status if final else "not_submitted", "overdue": overdue})
    return result


def available_sessions(user):
    if coordinator(user):
        return AcademicSession.objects.all()
    filters = Q(pk__in=[])
    if user.has_role(RoleCode.STUDENT):
        filters |= Q(student_enrollments__user=user)
    if lecturer_account(user):
        filters |= Q(student_enrollments__supervisor_assignments__lecturer__user=user)
        filters |= Q(defence_panels__members__user=user)
        filters |= Q(status="active")
    return AcademicSession.objects.filter(filters).distinct()


def perform_action(user, data, uploaded_file=None):
    """Use one session row lock for state transitions and allocation consistency."""
    check(isinstance(data, Mapping), "Provide a valid request object.")
    operation = text(data, "action", 40)
    uploaded_paths = []
    try:
        with transaction.atomic():
            session = get_row(AcademicSession, data.get("session"))
            session = AcademicSession.objects.select_for_update().get(pk=session.pk)
            require(available_sessions(user).filter(pk=session.pk).exists())
            if session.status != "active":
                project_id = data.get("project")
                closed_project = (
                    ProjectCompletion.objects.filter(
                        pk=uid(project_id),
                        enrollment__session=session,
                    ).first()
                    if project_id
                    else None
                )
                reopened_for_panel_integrity = bool(
                    closed_project
                    and closed_project.events.filter(
                        action="panel_reallocation_required"
                    ).exists()
                )
                reallocation_projects = ProjectCompletion.objects.filter(
                    enrollment__session=session,
                    status__in=["panel_reallocation_required", "scheduled"],
                    events__action="panel_reallocation_required",
                ).distinct()
                permitted_reallocation_setup = bool(
                    reallocation_projects.exists()
                    and (
                        (
                            operation in ("create_panel", "update_panel")
                            and coord
                            and reallocation_projects.exclude(
                                scores__round=F("score_round")
                            ).exists()
                        )
                        or (
                            operation == "save_scheme"
                            and lecturer_account(user)
                            and reallocation_projects.filter(
                                status="panel_reallocation_required",
                                enrollment__supervisor_assignments__is_current=True,
                                enrollment__supervisor_assignments__lecturer__user=user,
                            ).exclude(scores__round=F("score_round")).exists()
                        )
                    )
                )
                permitted_post_publication_action = bool(
                    closed_project
                    and operation in POST_PUBLICATION_ACTIONS
                    and (closed_project.published_at is not None or reopened_for_panel_integrity)
                )
                permitted_panel_reallocation = bool(
                    closed_project
                    and operation == "schedule"
                    and closed_project.status in ("panel_reallocation_required", "scheduled")
                    and reopened_for_panel_integrity
                    and not closed_project.scores.filter(round=closed_project.score_round).exists()
                )
                check(
                    session.status == "closed"
                    and (
                        permitted_post_publication_action
                        or permitted_panel_reallocation
                        or permitted_reallocation_setup
                    ),
                    "This academic session is not active.",
                )
            _perform(user, session, operation, data, uploaded_file, uploaded_paths)
    except Exception:
        for path in uploaded_paths:
            remove_report_document(path)
        raise
    return {"detail": "Saved successfully."}


def _perform(user, session, op, data, uploaded_file, uploaded_paths):
    coord = coordinator(user)
    own = StudentEnrollment.objects.filter(session=session, user=user, verification_status__in=VERIFIED_STATUSES).first() if user.has_role(RoleCode.STUDENT) else None
    if op == "set_deadline":
        require(coord)
        kind = text(data, "kind", 80)
        due = date(data.get("due_date"))
        if kind.startswith("section:"):
            section = get_row(ProjectReportSection, kind.split(":", 1)[1], session=session, is_active=True)
            section.due_date = due
            section.updated_by = user
            section.save(update_fields=["due_date", "updated_by", "updated_at"])
        else:
            check(kind in DEADLINE_KINDS, "Invalid deadline category.")
            ProjectDeadline.objects.update_or_create(session=session, kind=kind, defaults={"due_date": due, "updated_by": user})
        notify(StudentEnrollment.objects.filter(session=session, verification_status__in=VERIFIED_STATUSES).values_list("user_id", flat=True), "deadlines", "A project deadline has been updated.")
        return
    if op == "request_extension":
        require(own is not None)
        kind = text(data, "kind", 80)
        original = base_deadline(session, kind)
        check(original is not None, "There is no configured deadline for this activity.")
        requested = date(data.get("requested_date"))
        check(requested > effective_deadline(own, kind, original) and requested >= timezone.localdate(), "The proposed date must be later than the existing deadline and not in the past.")
        check(not DeadlineExtension.objects.filter(enrollment=own, kind=kind, status="pending").exists(), "An extension request is already awaiting a decision.")
        DeadlineExtension.objects.create(enrollment=own, kind=kind, original_due_date=original, requested_date=requested, justification=text(data, "justification"))
        notify(coordinators(), "deadlines", "A student has requested a deadline extension.")
        return
    if op in ("approve_extension", "reject_extension"):
        require(coord)
        extension = get_row(DeadlineExtension, data.get("extension"), enrollment__session=session)
        check(extension.status == "pending", "This request has already been decided.")
        extension.status = "approved" if op == "approve_extension" else "rejected"
        extension.decision_note = text(data, "note", required=op == "reject_extension")
        extension.decided_at = timezone.now()
        extension.decided_by = user
        extension.save()
        notify([extension.enrollment.user_id], "deadlines", "Your deadline extension request has been decided.")
        return
    if op == "save_scheme":
        require(
            lecturer_account(user),
            "Only a Lecturer account can configure an assessment structure.",
        )
        profile = LecturerProfile.objects.filter(user=user, is_active=True).first()
        require(profile is not None)
        components = normalize_components(data.get("components"))
        check(not ProjectCompletion.objects.filter(enrollment__session=session, enrollment__supervisor_assignments__lecturer=profile, enrollment__supervisor_assignments__is_current=True, panel__isnull=False).exists(), "The assessment structure is locked after a student's defence is allocated.")
        AssessmentScheme.objects.update_or_create(session=session, lecturer=profile, defaults={"components": components})
        return
    if op in ("create_panel", "update_panel"):
        require(coord)
        name = text(data, "name", 150)
        ids = data.get("members")
        check(isinstance(ids, list) and 1 <= len(ids) <= 30, "Choose one or more examiners.")
        ids = {uid(value) for value in ids}
        members = LecturerProfile.objects.filter(
            pk__in=ids,
            is_active=True,
            user__is_active=True,
            user__role_assignments__role__code=RoleCode.LECTURER,
        ).exclude(
            user__role_assignments__role__code=RoleCode.STUDENT
        ).exclude(
            user__student_enrollments__isnull=False
        ).distinct()
        check(members.count() == len(ids), "Select active lecturers only.")
        panel = get_row(DefencePanel, data.get("panel"), session=session) if op == "update_panel" else None
        check(not DefencePanel.objects.filter(session=session, name__iexact=name).exclude(pk=panel.pk if panel else None).exists(), "A panel with this name already exists.")
        if panel:
            check(not panel.projects.exists(), "An allocated panel cannot be edited. Create another panel and reallocate before scores are submitted.")
            panel.name = name
            panel.save(update_fields=["name"])
        else:
            panel = DefencePanel.objects.create(session=session, name=name, created_by=user)
        panel.members.set(members)
        return
    if op == "submit":
        require(own is not None)
        check(_current_assignment(own) is not None, "A current supervisor is required.")
        check(ProjectTopic.objects.filter(student_enrollment=own, is_current=True, status="approved").exists(), "Obtain approval for your project topic first.")
        sections = ProjectReportSection.objects.filter(session=session, is_active=True, is_required=True)
        check(sections.exists() and ProjectReportSubmission.objects.filter(student_enrollment=own, section__in=sections, status="approved").count() == sections.count(), "All required report sections must be approved before final submission.")
        check(not ProjectReportSubmission.objects.filter(student_enrollment=own, section__is_active=True).exclude(status="approved").exists(), "Complete all submitted report sections before final submission.")
        project = ProjectCompletion.objects.filter(enrollment=own).first()
        check(project is None or project.status in ("revision_requested", "clearance_denied"), "A final project has already been submitted.")
        check(uploaded_file is not None, "Choose a PDF or DOCX document.")
        note = text(data, "note", required=False)
        if not project:
            project = ProjectCompletion.objects.create(enrollment=own)
        path, metadata = upload_document(uploaded_file, own, "final")
        uploaded_paths.append(path)
        version = (project.documents.order_by("-version").values_list("version", flat=True).first() or 0) + 1
        FinalReportVersion.objects.create(project=project, version=version, storage_path=path, note=note, **metadata)
        project.status = "submitted"
        project.save(update_fields=["status", "updated_at"])
        event(project, user, op)
        return
    project = get_row(ProjectCompletion, data.get("project"), enrollment__session=session)
    project = ProjectCompletion.objects.select_for_update().get(pk=project.pk)
    sup = supervisor(user, project.enrollment)
    member = examiner(user, project)
    is_owner = own is not None and own.pk == project.enrollment_id
    state = project.status
    note = text(data, "note", required=False)
    check(project.enrollment.is_verified, "The student's registration must remain verified.")
    if op in ("recommend", "decline"):
        require(sup)
        check(state == "submitted", "Only a submitted final project can be reviewed.")
        check(op == "recommend" or bool(note), "Explain why revision is required.")
        project.status = "recommended" if op == "recommend" else "revision_requested"
    elif op in ("clear", "deny_clearance"):
        require(coord)
        check(state == "recommended", "Supervisor recommendation is required.")
        check(op == "clear" or bool(note), "Provide a reason for withholding clearance.")
        project.status = "cleared" if op == "clear" else "clearance_denied"
    elif op == "schedule":
        require(coord)
        check(
            state in ("cleared", "scheduled", "panel_reallocation_required")
            and not project.scores.filter(round=project.score_round).exists(),
            "Only cleared projects without scores in the current assessment round may be allocated.",
        )
        panel = get_row(DefencePanel, data.get("panel"), session=session)
        assignment = _current_assignment(project.enrollment)
        check(assignment is not None, "The student needs an active supervisor.")
        scheme = AssessmentScheme.objects.filter(session=session, lecturer=assignment.lecturer).first()
        check(scheme is not None, "The supervisor must configure the assessment structure first.")
        when = serializers.DateTimeField().run_validation(data.get("defence_at"))
        check(when >= timezone.now(), "Choose a future defence time.")
        check(not ProjectCompletion.objects.filter(enrollment__session=session, defence_at=when, panel__members__in=panel.members.all()).exclude(pk=project.pk).exists(), "An examiner already has a defence at that time.")
        project.panel = panel
        validate_panel(project)
        project.defence_at = when
        project.venue = text(data, "venue", 200)
        project.components = scheme.components
        project.status = "scheduled"
        event(project, user, op, note, {"panel": str(panel.pk), "panel_name": panel.name, "defence_at": when.isoformat(), "venue": project.venue, "components": project.components})
        project.save()
        return
    elif op == "score":
        require(member is not None)
        validate_panel(project)
        check(state in ("scheduled", "scoring", "correction"), "This project is not accepting scores.")
        check(project.defence_at and timezone.now() >= project.defence_at, "Scores can be submitted after the scheduled defence begins.")
        check(not project.scores.filter(examiner=member, round=project.score_round).exists(), "You have already submitted scores for this round.")
        ExaminerScore.objects.create(project=project, examiner=member, round=project.score_round, marks=normalize_marks(data.get("marks"), project.components))
        if state != "correction":
            project.status = "scoring"
    elif op in ("approve_result", "return_result", "publish"):
        require(
            independent_coordinator(user, project),
            "An examiner cannot approve, return or publish a result for a project they examined.",
        )
        validate_panel(project)
        if op == "approve_result":
            check(state in ("scoring", "correction") and result_for(project) is not None, "All examiners must submit scores for this round.")
            project.status = "approved"
        elif op == "return_result":
            check(state in ("scoring", "correction", "approved") and result_for(project) and bool(note), "A complete result and correction reason are required.")
            project.score_round += 1
            project.status = "correction"
        else:
            check(state == "approved" and result_for(project), "The result must be approved before publication.")
            project.published_result = result_for(project)
            project.published_at = project.published_at or timezone.now()
            project.status = "published"
    elif op == "appeal":
        require(is_owner)
        check(state == "published" and project.published_at and timezone.now() <= project.published_at + timedelta(days=14), "The 14-day appeal period has ended or the result is not published.")
        check(not project.appeals.filter(status__in=["pending", "reviewed"]).exists(), "An appeal is already open.")
        ResultAppeal.objects.create(project=project, complaint=text(data, "complaint"))
    elif op == "review_appeal":
        require(member is not None)
        validate_panel(project)
        check(state == "published", "Only a published result can be appealed.")
        appeal = get_row(ResultAppeal, data.get("appeal"), project=project)
        check(appeal.status == "pending" and bool(note), "A pending appeal and panel feedback are required.")
        appeal.status = "reviewed"
        appeal.panel_feedback = note
        appeal.panel_reviewer = user
        appeal.reviewed_at = timezone.now()
        appeal.save()
    elif op in ("accept_appeal", "reject_appeal"):
        require(
            independent_coordinator(user, project),
            "An examiner cannot make the Coordinator's appeal decision for a project they examined.",
        )
        check(state == "published", "The appeal requires a published result.")
        appeal = get_row(ResultAppeal, data.get("appeal"), project=project)
        check(appeal.status == "reviewed" and bool(note), "Panel feedback and a Coordinator decision are required.")
        appeal.status = "accepted" if op == "accept_appeal" else "rejected"
        appeal.decision_note = note
        appeal.decided_by = user
        appeal.decided_at = timezone.now()
        appeal.save()
        if op == "accept_appeal":
            project.score_round += 1
            project.status = "correction"
    else:
        raise ValidationError({"detail": "Unknown project action."})
    project.save()
    event(project, user, op, note, {"round": project.score_round, "result": project.published_result if op == "publish" else {}}, category="appeals" if "appeal" in op else "results" if op in ("approve_result", "return_result", "publish", "score") else "defence")
