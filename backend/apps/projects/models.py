import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


class ProjectTopicStatus(models.TextChoices):
    SUBMITTED = "submitted", "Submitted"
    REVISION_REQUESTED = "revision_requested", "Revision requested"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


class ProjectTopicDecision(models.TextChoices):
    APPROVE = "approve", "Approve"
    REQUEST_REVISION = "request_revision", "Request revision"
    REJECT = "reject", "Reject"


class ProjectTopic(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student_enrollment = models.ForeignKey(
        "academics.StudentEnrollment",
        on_delete=models.PROTECT,
        related_name="project_topics",
    )
    supervisor_assignment = models.ForeignKey(
        "academics.SupervisorAssignment",
        on_delete=models.PROTECT,
        related_name="project_topics",
    )
    title = models.CharField(max_length=300)
    abstract = models.TextField()
    problem_statement = models.TextField()
    research_objectives = models.TextField()
    keywords = models.JSONField(default=list)
    status = models.CharField(
        max_length=24,
        choices=ProjectTopicStatus.choices,
        default=ProjectTopicStatus.SUBMITTED,
    )
    is_current = models.BooleanField(default=True)
    submitted_at = models.DateTimeField(default=timezone.now)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "projects_project_topic"
        ordering = ["-submitted_at", "title"]
        constraints = [
            models.UniqueConstraint(
                fields=["student_enrollment"],
                condition=Q(is_current=True),
                name="projects_one_current_topic_per_student",
            )
        ]
        indexes = [
            models.Index(fields=["status", "submitted_at"], name="projects_topic_status_idx"),
            models.Index(fields=["supervisor_assignment", "status"], name="projects_topic_supervisor_idx"),
        ]

    def __str__(self):
        return f"{self.title} ({self.student_enrollment.matric_number})"


class ProjectTopicRevision(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    topic = models.ForeignKey(
        ProjectTopic,
        on_delete=models.CASCADE,
        related_name="revisions",
    )
    revision_number = models.PositiveIntegerField()
    title = models.CharField(max_length=300)
    abstract = models.TextField()
    problem_statement = models.TextField()
    research_objectives = models.TextField()
    keywords = models.JSONField(default=list)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="project_topic_revisions",
    )
    submitted_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "projects_project_topic_revision"
        ordering = ["revision_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["topic", "revision_number"],
                name="projects_unique_topic_revision",
            )
        ]

    def __str__(self):
        return f"{self.topic_id} revision {self.revision_number}"


class ProjectTopicReview(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    topic = models.ForeignKey(
        ProjectTopic,
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    revision = models.ForeignKey(
        ProjectTopicRevision,
        on_delete=models.PROTECT,
        related_name="reviews",
    )
    supervisor_assignment = models.ForeignKey(
        "academics.SupervisorAssignment",
        on_delete=models.PROTECT,
        related_name="project_topic_reviews",
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="project_topic_reviews",
    )
    decision = models.CharField(max_length=24, choices=ProjectTopicDecision.choices)
    feedback = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "projects_project_topic_review"
        ordering = ["-reviewed_at"]
        indexes = [
            models.Index(fields=["topic", "reviewed_at"], name="projects_topic_review_idx"),
        ]

    def __str__(self):
        return f"{self.topic_id}: {self.get_decision_display()}"
