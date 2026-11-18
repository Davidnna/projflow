from rest_framework import serializers

from apps.accounts.models import RoleCode

from .models import (
    ProjectTopic,
    ProjectTopicDecision,
    ProjectTopicReview,
    ProjectTopicRevision,
    ProjectTopicSimilarity,
    ProjectTopicStatus,
)


class ProjectTopicSubmissionSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=300, trim_whitespace=True)
    abstract = serializers.CharField(max_length=10000, trim_whitespace=True)
    problem_statement = serializers.CharField(max_length=10000, trim_whitespace=True)
    research_objectives = serializers.CharField(max_length=8000, trim_whitespace=True)
    keywords = serializers.ListField(
        child=serializers.CharField(max_length=60, trim_whitespace=True),
        min_length=1,
        max_length=15,
        allow_empty=False,
    )

    def validate_keywords(self, value):
        cleaned = []
        seen = set()
        for keyword in value:
            item = " ".join(keyword.split())
            key = item.casefold()
            if item and key not in seen:
                cleaned.append(item)
                seen.add(key)
        if not cleaned:
            raise serializers.ValidationError("Enter at least one project keyword.")
        return cleaned


class ProjectTopicReviewActionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=ProjectTopicDecision.choices)
    feedback = serializers.CharField(required=False, allow_blank=True, max_length=5000)

    def validate(self, attrs):
        if attrs["decision"] in {
            ProjectTopicDecision.REQUEST_REVISION,
            ProjectTopicDecision.REJECT,
        } and not attrs.get("feedback", "").strip():
            raise serializers.ValidationError({"feedback": "Feedback is required for this decision."})
        return attrs


class ProjectTopicRevisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectTopicRevision
        fields = [
            "id",
            "revision_number",
            "title",
            "abstract",
            "problem_statement",
            "research_objectives",
            "keywords",
            "submitted_at",
        ]


class ProjectTopicReviewSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.CharField(source="reviewer.get_full_name", read_only=True)
    revision_number = serializers.IntegerField(source="revision.revision_number", read_only=True)

    class Meta:
        model = ProjectTopicReview
        fields = [
            "id",
            "revision_number",
            "decision",
            "feedback",
            "reviewer_name",
            "reviewed_at",
        ]


class ProjectTopicSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student_enrollment.user.get_full_name", read_only=True)
    matric_number = serializers.CharField(source="student_enrollment.matric_number", read_only=True)
    session_name = serializers.CharField(source="student_enrollment.session.name", read_only=True)
    supervisor_name = serializers.CharField(
        source="supervisor_assignment.lecturer.user.get_full_name",
        read_only=True,
    )
    revisions = ProjectTopicRevisionSerializer(many=True, read_only=True)
    reviews = ProjectTopicReviewSerializer(many=True, read_only=True)
    revision_count = serializers.IntegerField(source="revisions.count", read_only=True)
    can_review = serializers.SerializerMethodField()
    can_view_similarity = serializers.SerializerMethodField()

    def get_can_view_similarity(self, obj):
        request = self.context.get("request")
        if request is None or not request.user.is_authenticated:
            return False
        if (
            request.user.is_superuser
            or request.user.has_role(RoleCode.ADMINISTRATOR)
            or request.user.has_role(RoleCode.PROJECT_COORDINATOR)
            or not request.user.has_role(RoleCode.LECTURER)
        ):
            return False
        assignment = obj.supervisor_assignment
        return assignment.is_current and assignment.lecturer.user_id == request.user.id

    def get_can_review(self, obj):
        request = self.context.get("request")
        if request is None or not request.user.is_authenticated:
            return False
        if not request.user.has_role(RoleCode.LECTURER):
            return False
        assignment = obj.supervisor_assignment
        return (
            obj.status == ProjectTopicStatus.SUBMITTED
            and obj.is_current
            and assignment.is_current
            and assignment.lecturer.user_id == request.user.id
        )

    class Meta:
        model = ProjectTopic
        fields = [
            "id",
            "student_name",
            "matric_number",
            "session_name",
            "supervisor_name",
            "title",
            "abstract",
            "problem_statement",
            "research_objectives",
            "keywords",
            "status",
            "is_current",
            "submitted_at",
            "reviewed_at",
            "revision_count",
            "can_review",
            "can_view_similarity",
            "revisions",
            "reviews",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ProjectTopicSimilaritySerializer(serializers.ModelSerializer):
    previous_title = serializers.CharField(source="matched_revision.title", read_only=True)
    academic_session = serializers.CharField(
        source="matched_revision.topic.student_enrollment.session.name",
        read_only=True,
    )
    project_status = serializers.CharField(source="matched_revision.topic.status", read_only=True)
    project_status_label = serializers.CharField(
        source="matched_revision.topic.get_status_display",
        read_only=True,
    )
    similarity_percent = serializers.SerializerMethodField()
    matched_sections = serializers.SerializerMethodField()

    class Meta:
        model = ProjectTopicSimilarity
        fields = [
            "id",
            "previous_title",
            "academic_session",
            "project_status",
            "project_status_label",
            "similarity_percent",
            "matched_sections",
        ]

    def get_similarity_percent(self, obj):
        return round(obj.overall_score * 100, 1)

    def get_matched_sections(self, obj):
        from .similarity import FIELD_LABELS, MATCHED_SECTION_THRESHOLD

        sections = []
        revision = obj.matched_revision
        for field, label in FIELD_LABELS.items():
            score = float((obj.field_scores or {}).get(field, 0.0))
            if score < MATCHED_SECTION_THRESHOLD:
                continue
            if field == "keywords":
                content = ", ".join(revision.keywords or [])
            else:
                content = getattr(revision, field)
            excerpt = " ".join(str(content).split())
            if len(excerpt) > 420:
                excerpt = f"{excerpt[:417].rstrip()}..."
            sections.append(
                {
                    "section": label,
                    "similarity_percent": round(score * 100, 1),
                    "excerpt": excerpt,
                }
            )
        return sections
