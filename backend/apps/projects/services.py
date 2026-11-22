from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.models import RoleCode
from apps.academics.models import (
    AcademicSessionStatus,
    StudentEnrollment,
    SupervisorAssignment,
)

from .models import (
    ProjectTopic,
    ProjectTopicDecision,
    ProjectTopicRevision,
    ProjectTopicStatus,
    ProjectTopicReview,
)


def _clean_topic_data(data):
    keywords = data.get("keywords", [])
    cleaned_keywords = []
    seen = set()
    for keyword in keywords:
        value = " ".join(str(keyword).strip().split())
        key = value.casefold()
        if value and key not in seen:
            cleaned_keywords.append(value)
            seen.add(key)
    if not cleaned_keywords:
        raise ValidationError({"keywords": "Enter at least one project keyword."})
    return {
        "title": " ".join(data["title"].strip().split()),
        "abstract": data["abstract"].strip(),
        "problem_statement": data["problem_statement"].strip(),
        "research_objectives": data["research_objectives"].strip(),
        "keywords": cleaned_keywords,
    }


def _create_revision(*, topic, actor, revision_number):
    return ProjectTopicRevision.objects.create(
        topic=topic,
        revision_number=revision_number,
        title=topic.title,
        abstract=topic.abstract,
        problem_statement=topic.problem_statement,
        research_objectives=topic.research_objectives,
        keywords=topic.keywords,
        submitted_by=actor,
    )


@transaction.atomic
def submit_project_topic(*, actor, data):
    if not actor.has_role(RoleCode.STUDENT):
        raise ValidationError("Only students can submit project topics.")

    enrollment = (
        StudentEnrollment.objects.select_for_update()
        .select_related("session")
        .filter(user=actor, session__status=AcademicSessionStatus.ACTIVE)
        .order_by("-created_at")
        .first()
    )
    if enrollment is None or not enrollment.is_verified:
        raise ValidationError("Your student registration must be verified before submitting a project topic.")

    assignment = (
        SupervisorAssignment.objects.select_for_update()
        .select_related("lecturer__user")
        .filter(student_enrollment=enrollment, is_current=True)
        .first()
    )
    if assignment is None:
        raise ValidationError("A supervisor must be assigned before you can submit a project topic.")
    if not assignment.lecturer.is_active or not assignment.lecturer.user.is_active:
        raise ValidationError("Your assigned supervisor is currently unavailable. Please contact your department.")

    if ProjectTopic.objects.filter(student_enrollment=enrollment, is_current=True).exists():
        raise ValidationError("You already have an active project topic. Review its current status before submitting another proposal.")

    cleaned = _clean_topic_data(data)
    try:
        topic = ProjectTopic.objects.create(
            student_enrollment=enrollment,
            supervisor_assignment=assignment,
            **cleaned,
        )
        _create_revision(topic=topic, actor=actor, revision_number=1)
    except IntegrityError as exc:
        raise ValidationError("A project topic is already active for your registration. Refresh and try again.") from exc
    from .lifecycle import notify
    notify([assignment.lecturer.user_id], "topics", "A new project topic is awaiting your review.")
    return topic


@transaction.atomic
def resubmit_project_topic(*, topic_id, actor, data):
    topic = (
        ProjectTopic.objects.select_for_update()
        .select_related("student_enrollment", "student_enrollment__session")
        .get(pk=topic_id)
    )
    if topic.student_enrollment.user_id != actor.id:
        raise ValidationError("You can only revise your own project topic.")
    if topic.status != ProjectTopicStatus.REVISION_REQUESTED or not topic.is_current:
        raise ValidationError("This project topic is not awaiting revision.")
    if topic.student_enrollment.session.status != AcademicSessionStatus.ACTIVE:
        raise ValidationError("Project topics can only be revised during the active academic session.")

    assignment = (
        SupervisorAssignment.objects.select_for_update()
        .select_related("lecturer__user")
        .filter(student_enrollment=topic.student_enrollment, is_current=True)
        .first()
    )
    if assignment is None:
        raise ValidationError("A current supervisor assignment is required to resubmit this topic.")
    if not assignment.lecturer.is_active or not assignment.lecturer.user.is_active:
        raise ValidationError("Your assigned supervisor is currently unavailable. Please contact your department.")

    cleaned = _clean_topic_data(data)
    for field, value in cleaned.items():
        setattr(topic, field, value)
    topic.supervisor_assignment = assignment
    topic.status = ProjectTopicStatus.SUBMITTED
    topic.submitted_at = timezone.now()
    topic.reviewed_at = None
    topic.save(
        update_fields=[
            "title",
            "abstract",
            "problem_statement",
            "research_objectives",
            "keywords",
            "supervisor_assignment",
            "status",
            "submitted_at",
            "reviewed_at",
            "updated_at",
        ]
    )
    revision_number = topic.revisions.count() + 1
    _create_revision(topic=topic, actor=actor, revision_number=revision_number)
    from .lifecycle import notify
    notify([assignment.lecturer.user_id], "topics", "A revised project topic is awaiting your review.")
    return topic


@transaction.atomic
def review_project_topic(*, topic_id, actor, decision, feedback=""):
    topic = (
        ProjectTopic.objects.select_for_update()
        .select_related(
            "student_enrollment__session",
            "supervisor_assignment__lecturer__user",
        )
        .get(pk=topic_id)
    )
    assignment = topic.supervisor_assignment
    if not actor.has_role(RoleCode.LECTURER):
        raise ValidationError("Only the assigned supervisor can review a project topic.")
    if assignment.lecturer.user_id != actor.id or not assignment.is_current:
        raise ValidationError("Only the student's currently assigned supervisor can review this project topic.")
    if not assignment.lecturer.is_active or not assignment.lecturer.user.is_active:
        raise ValidationError("This supervisor account is not active.")
    if topic.status != ProjectTopicStatus.SUBMITTED or not topic.is_current:
        raise ValidationError("This project topic is not awaiting a supervisor decision.")
    if decision not in ProjectTopicDecision.values:
        raise ValidationError("Select a valid review decision.")
    feedback = feedback.strip()
    if decision in {ProjectTopicDecision.REQUEST_REVISION, ProjectTopicDecision.REJECT} and not feedback:
        raise ValidationError({"feedback": "Feedback is required for a revision request or rejection."})

    revision = topic.revisions.order_by("-revision_number").first()
    if revision is None:
        raise ValidationError("The submitted project topic could not be found.")

    ProjectTopicReview.objects.create(
        topic=topic,
        revision=revision,
        supervisor_assignment=assignment,
        reviewer=actor,
        decision=decision,
        feedback=feedback,
    )

    if decision == ProjectTopicDecision.APPROVE:
        topic.status = ProjectTopicStatus.APPROVED
    elif decision == ProjectTopicDecision.REQUEST_REVISION:
        topic.status = ProjectTopicStatus.REVISION_REQUESTED
    else:
        topic.status = ProjectTopicStatus.REJECTED
        topic.is_current = False
    topic.reviewed_at = timezone.now()
    topic.save(update_fields=["status", "is_current", "reviewed_at", "updated_at"])
    from .lifecycle import notify
    notify([topic.student_enrollment.user_id], "topics", "Your supervisor has reviewed your project topic.")
    return topic
