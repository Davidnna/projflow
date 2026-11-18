from rest_framework import serializers

from apps.accounts.models import RoleCode
from apps.academics.models import AcademicSessionStatus

from .models import (
    ProjectMilestone,
    ProjectProgressReport,
    ProjectProgressReview,
    ProjectProgressRevision,
    ProgressAssessment,
    ProgressReviewDecision,
)


class ProjectMilestoneSerializer(serializers.ModelSerializer):
    session_name = serializers.CharField(source="session.name", read_only=True)
    session_status = serializers.CharField(source="session.status", read_only=True)
    report_count = serializers.SerializerMethodField()

    class Meta:
        model = ProjectMilestone
        fields = [
            "id",
            "session",
            "session_name",
            "session_status",
            "title",
            "description",
            "expected_achievement",
            "sequence",
            "due_date",
            "is_active",
            "report_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
        extra_kwargs = {"sequence": {"min_value": 1}}

    def get_report_count(self, obj):
        request = self.context.get("request")
        if request is None or not request.user.is_authenticated:
            return None
        if (
            request.user.is_superuser
            or request.user.has_role(RoleCode.ADMINISTRATOR)
            or request.user.has_role(RoleCode.PROJECT_COORDINATOR)
        ):
            return obj.progress_reports.count()
        return None

    def validate(self, attrs):
        instance = self.instance
        session = attrs.get("session", getattr(instance, "session", None))
        sequence = attrs.get("sequence", getattr(instance, "sequence", None))
        if session and session.status == AcademicSessionStatus.CLOSED:
            raise serializers.ValidationError({"session": "Milestones cannot be changed in a closed academic session."})
        if session and sequence is not None:
            existing = ProjectMilestone.objects.filter(session=session, sequence=sequence)
            if instance:
                existing = existing.exclude(pk=instance.pk)
            if existing.exists():
                raise serializers.ValidationError({"sequence": "This milestone position is already used in the selected session."})
        if instance and instance.progress_reports.exists():
            protected_fields = {
                "session": session,
                "sequence": sequence,
                "title": attrs.get("title", instance.title),
                "description": attrs.get("description", instance.description),
                "expected_achievement": attrs.get("expected_achievement", instance.expected_achievement),
            }
            if (
                protected_fields["session"].pk != instance.session_id
                or protected_fields["sequence"] != instance.sequence
                or protected_fields["title"] != instance.title
                or protected_fields["description"] != instance.description
                or protected_fields["expected_achievement"] != instance.expected_achievement
            ):
                raise serializers.ValidationError(
                    "The milestone structure cannot be changed after students have submitted reports. You can still update its due date or availability."
                )
        return attrs


class ProjectProgressRevisionSerializer(serializers.ModelSerializer):
    submitted_by_name = serializers.CharField(source="submitted_by.get_full_name", read_only=True)

    class Meta:
        model = ProjectProgressRevision
        fields = [
            "id",
            "revision_number",
            "completed_activities",
            "challenges",
            "next_steps",
            "submitted_by_name",
            "submitted_at",
        ]
        read_only_fields = fields


class ProjectProgressReviewSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.CharField(source="reviewer.get_full_name", read_only=True)
    revision_number = serializers.IntegerField(source="revision.revision_number", read_only=True)

    class Meta:
        model = ProjectProgressReview
        fields = [
            "id",
            "revision_number",
            "decision",
            "assessment",
            "feedback",
            "reviewer_name",
            "reviewed_at",
        ]
        read_only_fields = fields


class ProjectProgressReportSerializer(serializers.ModelSerializer):
    milestone_title = serializers.CharField(source="milestone.title", read_only=True)
    session_name = serializers.CharField(source="milestone.session.name", read_only=True)
    student_name = serializers.CharField(source="student_enrollment.user.get_full_name", read_only=True)
    matric_number = serializers.CharField(source="student_enrollment.matric_number", read_only=True)
    supervisor_name = serializers.SerializerMethodField()
    revisions = ProjectProgressRevisionSerializer(many=True, read_only=True)
    reviews = ProjectProgressReviewSerializer(many=True, read_only=True)
    latest_revision = serializers.SerializerMethodField()
    can_review = serializers.SerializerMethodField()
    can_resubmit = serializers.SerializerMethodField()

    class Meta:
        model = ProjectProgressReport
        fields = [
            "id",
            "milestone",
            "milestone_title",
            "session_name",
            "student_name",
            "matric_number",
            "supervisor_name",
            "status",
            "submitted_at",
            "reviewed_at",
            "created_at",
            "updated_at",
            "latest_revision",
            "revisions",
            "reviews",
            "can_review",
            "can_resubmit",
        ]
        read_only_fields = fields

    def get_supervisor_name(self, obj):
        assignment = obj.student_enrollment.supervisor_assignments.filter(
            is_current=True,
        ).select_related("lecturer__user").first()
        if assignment is None:
            assignment = obj.supervisor_assignment
        return assignment.lecturer.user.get_full_name()

    def get_latest_revision(self, obj):
        revision = obj.revisions.order_by("-revision_number").first()
        if revision is None:
            return None
        return ProjectProgressRevisionSerializer(revision).data

    def get_can_review(self, obj):
        request = self.context.get("request")
        if request is None or not request.user.is_authenticated or not request.user.has_role(RoleCode.LECTURER):
            return False
        if obj.status != "submitted":
            return False
        return obj.student_enrollment.supervisor_assignments.filter(
            is_current=True,
            lecturer__user=request.user,
            lecturer__is_active=True,
        ).exists()

    def get_can_resubmit(self, obj):
        request = self.context.get("request")
        return bool(
            request
            and request.user.is_authenticated
            and request.user.has_role(RoleCode.STUDENT)
            and obj.student_enrollment.user_id == request.user.id
            and obj.status == "revision_requested"
        )


class ProjectProgressReportSubmissionSerializer(serializers.Serializer):
    milestone = serializers.PrimaryKeyRelatedField(queryset=ProjectMilestone.objects.filter(is_active=True))
    completed_activities = serializers.CharField(max_length=10000, trim_whitespace=True)
    challenges = serializers.CharField(max_length=5000, required=False, allow_blank=True, trim_whitespace=True)
    next_steps = serializers.CharField(max_length=5000, required=False, allow_blank=True, trim_whitespace=True)


class ProjectProgressRevisionSubmissionSerializer(serializers.Serializer):
    completed_activities = serializers.CharField(max_length=10000, trim_whitespace=True)
    challenges = serializers.CharField(max_length=5000, required=False, allow_blank=True, trim_whitespace=True)
    next_steps = serializers.CharField(max_length=5000, required=False, allow_blank=True, trim_whitespace=True)


class ProjectProgressReviewActionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=ProgressReviewDecision.choices)
    assessment = serializers.ChoiceField(choices=ProgressAssessment.choices)
    feedback = serializers.CharField(required=False, allow_blank=True, max_length=5000)

    def validate(self, attrs):
        feedback_required = (
            attrs["decision"] == ProgressReviewDecision.REQUEST_REVISION
            or attrs["assessment"] in {
                ProgressAssessment.NEEDS_ATTENTION,
                ProgressAssessment.BEHIND_SCHEDULE,
            }
        )
        if feedback_required and not attrs.get("feedback", "").strip():
            raise serializers.ValidationError({"feedback": "Feedback is required for this assessment."})
        if (
            attrs["decision"] == ProgressReviewDecision.REQUEST_REVISION
            and attrs["assessment"] == ProgressAssessment.COMPLETED
        ):
            raise serializers.ValidationError({"assessment": "A completed milestone cannot be returned for revision."})
        return attrs
