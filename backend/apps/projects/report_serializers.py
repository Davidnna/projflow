from rest_framework import serializers

from apps.accounts.models import RoleCode
from apps.academics.models import AcademicSession, AcademicSessionStatus

from .models import (
    ProjectReportRevision,
    ProjectReportReview,
    ProjectReportSection,
    ProjectReportSubmission,
    ReportReviewDecision,
)
from .report_files import inspect_report_document


class ProjectReportSectionSerializer(serializers.ModelSerializer):
    session_name = serializers.CharField(source="session.name", read_only=True)
    session_status = serializers.CharField(source="session.status", read_only=True)
    submission_count = serializers.SerializerMethodField()

    class Meta:
        model = ProjectReportSection
        fields = [
            "id",
            "session",
            "session_name",
            "session_status",
            "title",
            "description",
            "sequence",
            "due_date",
            "is_required",
            "is_active",
            "submission_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
        extra_kwargs = {"sequence": {"min_value": 1}}

    def get_submission_count(self, obj):
        request = self.context.get("request")
        if request is None or not request.user.is_authenticated:
            return None
        if request.user.has_role(RoleCode.PROJECT_COORDINATOR):
            return obj.submissions.count()
        return None

    def validate(self, attrs):
        instance = self.instance
        session = attrs.get("session", getattr(instance, "session", None))
        sequence = attrs.get("sequence", getattr(instance, "sequence", None))
        if session and session.status == AcademicSessionStatus.CLOSED:
            raise serializers.ValidationError({"session": "The report structure cannot be changed in a closed academic session."})
        if session and sequence is not None:
            existing = ProjectReportSection.objects.filter(session=session, sequence=sequence)
            if instance:
                existing = existing.exclude(pk=instance.pk)
            if existing.exists():
                raise serializers.ValidationError({"sequence": "This position is already used in the selected report structure."})

        session_has_submissions = bool(
            session
            and ProjectReportSubmission.objects.filter(section__session=session).exists()
        )
        instance_session_has_submissions = bool(
            instance
            and ProjectReportSubmission.objects.filter(section__session_id=instance.session_id).exists()
        )
        if instance and (session_has_submissions or instance_session_has_submissions):
            structural_fields = {
                "session": session,
                "title": attrs.get("title", instance.title),
                "description": attrs.get("description", instance.description),
                "sequence": sequence,
                "is_required": attrs.get("is_required", instance.is_required),
            }
            if (
                structural_fields["session"].pk != instance.session_id
                or structural_fields["title"] != instance.title
                or structural_fields["description"] != instance.description
                or structural_fields["sequence"] != instance.sequence
                or structural_fields["is_required"] != instance.is_required
            ):
                raise serializers.ValidationError(
                    "The report structure is already in use. Its section names and order can no longer be changed."
                )
            changed_fields = set(attrs) - {"due_date"}
            if changed_fields:
                raise serializers.ValidationError(
                    "Only the due date can be changed after students have started submitting report sections."
                )
        elif not instance and session_has_submissions:
            maximum_sequence = ProjectReportSection.objects.filter(
                session=session
            ).order_by("-sequence").values_list("sequence", flat=True).first() or 0
            if sequence is not None and sequence <= maximum_sequence:
                raise serializers.ValidationError(
                    {"sequence": "New sections must be added after the existing report sections."}
                )
        return attrs


class StandardReportStructureSerializer(serializers.Serializer):
    session = serializers.PrimaryKeyRelatedField(queryset=AcademicSession.objects.all())

    def validate_session(self, value):
        if value.status == AcademicSessionStatus.CLOSED:
            raise serializers.ValidationError("A report structure cannot be created for a closed academic session.")
        if value.project_report_sections.exists():
            raise serializers.ValidationError("A report structure already exists for this academic session.")
        return value


class ProjectReportRevisionSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(source="uploaded_by.get_full_name", read_only=True)
    download_path = serializers.SerializerMethodField()

    class Meta:
        model = ProjectReportRevision
        fields = [
            "id",
            "revision_number",
            "original_filename",
            "file_size",
            "content_type",
            "submission_note",
            "uploaded_by_name",
            "submitted_at",
            "download_path",
        ]
        read_only_fields = fields

    def get_download_path(self, obj):
        return (
            f"/api/projects/report-submissions/{obj.submission_id}/"
            f"revisions/{obj.pk}/download/"
        )


class ProjectReportReviewSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.CharField(source="reviewer.get_full_name", read_only=True)
    revision_number = serializers.IntegerField(source="revision.revision_number", read_only=True)
    annotation_download_path = serializers.SerializerMethodField()

    class Meta:
        model = ProjectReportReview
        fields = [
            "id",
            "revision_number",
            "decision",
            "feedback",
            "reviewer_name",
            "reviewed_at",
            "annotation_filename",
            "annotation_download_path",
        ]
        read_only_fields = fields

    def get_annotation_download_path(self, obj):
        if obj.annotation_path:
            return f"/api/projects/report-submissions/{obj.submission_id}/reviews/{obj.pk}/download/"
        return None


def can_access_current_report(submission, user):
    return bool(
        (user.has_role(RoleCode.STUDENT) and submission.student_enrollment.user_id == user.pk)
        or (user.has_role(RoleCode.LECTURER) and submission.student_enrollment.supervisor_assignments.filter(
            is_current=True, lecturer__user=user, lecturer__is_active=True, lecturer__user__is_active=True,
        ).exists())
    )


class ProjectReportSubmissionSerializer(serializers.ModelSerializer):
    section_title = serializers.CharField(source="section.title", read_only=True)
    section_sequence = serializers.IntegerField(source="section.sequence", read_only=True)
    session_name = serializers.CharField(source="section.session.name", read_only=True)
    student_name = serializers.CharField(source="student_enrollment.user.get_full_name", read_only=True)
    matric_number = serializers.CharField(source="student_enrollment.matric_number", read_only=True)
    supervisor_name = serializers.SerializerMethodField()
    revisions = serializers.SerializerMethodField()
    reviews = serializers.SerializerMethodField()
    latest_revision = serializers.SerializerMethodField()
    can_review = serializers.SerializerMethodField()
    can_resubmit = serializers.SerializerMethodField()

    class Meta:
        model = ProjectReportSubmission
        fields = [
            "id",
            "section",
            "section_title",
            "section_sequence",
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

    def visible_revisions(self, obj):
        request = self.context.get("request")
        if request is None or can_access_current_report(obj, request.user):
            return obj.revisions.all()
        return obj.revisions.filter(reviews__reviewer=request.user).distinct()

    def get_revisions(self, obj):
        return ProjectReportRevisionSerializer(self.visible_revisions(obj), many=True).data

    def get_reviews(self, obj):
        request = self.context.get("request")
        reviews = obj.reviews.all()
        if request is not None and not can_access_current_report(obj, request.user):
            reviews = reviews.filter(reviewer=request.user)
        return ProjectReportReviewSerializer(reviews, many=True).data

    def get_latest_revision(self, obj):
        revision = self.visible_revisions(obj).order_by("-revision_number").first()
        if revision is None:
            return None
        return ProjectReportRevisionSerializer(revision).data

    def get_can_review(self, obj):
        request = self.context.get("request")
        return bool(
            request
            and request.user.is_authenticated
            and request.user.has_role(RoleCode.LECTURER)
            and obj.section.session.status == AcademicSessionStatus.ACTIVE
            and obj.status == "submitted"
            and obj.student_enrollment.supervisor_assignments.filter(
                is_current=True,
                lecturer__user=request.user,
                lecturer__is_active=True,
                lecturer__user__is_active=True,
            ).exists()
        )

    def get_can_resubmit(self, obj):
        request = self.context.get("request")
        return bool(
            request
            and request.user.is_authenticated
            and request.user.has_role(RoleCode.STUDENT)
            and obj.student_enrollment.user_id == request.user.id
            and obj.status == "revision_requested"
        )


class ReportSubmissionUploadSerializer(serializers.Serializer):
    section = serializers.PrimaryKeyRelatedField(
        queryset=ProjectReportSection.objects.filter(is_active=True),
        required=True,
    )
    file = serializers.FileField(required=True, write_only=True)
    submission_note = serializers.CharField(required=False, allow_blank=True, max_length=5000)

    def validate_file(self, value):
        inspect_report_document(value)
        return value


class ReportRevisionUploadSerializer(serializers.Serializer):
    file = serializers.FileField(required=True, write_only=True)
    submission_note = serializers.CharField(required=False, allow_blank=True, max_length=5000)

    def validate_file(self, value):
        inspect_report_document(value)
        return value


class ReportReviewActionSerializer(serializers.Serializer):
    annotation = serializers.FileField(required=False, write_only=True)

    def validate_annotation(self, value):
        inspect_report_document(value)
        return value

    decision = serializers.ChoiceField(choices=ReportReviewDecision.choices)
    feedback = serializers.CharField(required=False, allow_blank=True, max_length=5000)

    def validate(self, attrs):
        if (
            attrs["decision"] == ReportReviewDecision.REQUEST_REVISION
            and not attrs.get("feedback", "").strip()
        ):
            raise serializers.ValidationError({"feedback": "Provide feedback explaining the changes required."})
        return attrs
