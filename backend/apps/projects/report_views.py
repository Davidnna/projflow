from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed, PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response

from apps.accounts.models import RoleCode
from apps.academics.models import StudentEnrollment, StudentVerificationStatus, SupervisorAssignment

from .models import (
    ProjectReportRevision,
    ProjectReportReview,
    ProjectReportSection,
    ProjectReportSubmission,
    ReportReviewDecision,
)
from .report_files import ReportStorageError, create_report_download_url
from .report_serializers import (
    ProjectReportSectionSerializer,
    ProjectReportSubmissionSerializer,
    ReportRevisionUploadSerializer,
    ReportReviewActionSerializer,
    ReportSubmissionUploadSerializer,
    StandardReportStructureSerializer,
)
from .report_services import (
    resubmit_report_section,
    review_report_section,
    submit_report_section,
)


class IsProjectCoordinator(BasePermission):
    message = "Only the Project Coordinator can manage the report structure."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.has_role(RoleCode.PROJECT_COORDINATOR))


def raise_api_validation_error(exc):
    if isinstance(exc, DjangoValidationError):
        if hasattr(exc, "message_dict"):
            raise ValidationError(exc.message_dict)
        raise ValidationError(exc.messages)
    raise exc


class ProjectReportSectionViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectReportSectionSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "put", "patch", "head", "options"]

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "create_standard_structure"}:
            return [IsProjectCoordinator()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        queryset = ProjectReportSection.objects.select_related(
            "session",
            "created_by",
            "updated_by",
        ).order_by("session__created_at", "sequence")
        if user.is_superuser or user.has_role(RoleCode.ADMINISTRATOR) or user.has_role(RoleCode.PROJECT_COORDINATOR):
            return queryset

        session_ids = set()
        if user.has_role(RoleCode.STUDENT):
            session_ids.update(
                StudentEnrollment.objects.filter(
                    user=user,
                    verification_status__in=[
                        StudentVerificationStatus.AUTO_VERIFIED,
                        StudentVerificationStatus.MANUALLY_APPROVED,
                    ],
                ).values_list("session_id", flat=True)
            )
        if user.has_role(RoleCode.LECTURER):
            session_ids.update(
                SupervisorAssignment.objects.filter(
                    lecturer__user=user,
                    lecturer__is_active=True,
                    is_current=True,
                ).values_list("student_enrollment__session_id", flat=True)
            )
        if not session_ids:
            return queryset.none()
        return queryset.filter(session_id__in=session_ids)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    @action(detail=False, methods=["post"], url_path="create-standard-structure")
    def create_standard_structure(self, request):
        serializer = StandardReportStructureSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session = serializer.validated_data["session"]
        standard_sections = [
            (
                "Preliminary Pages",
                "Combine the title page, declaration, certification, dedication, acknowledgements, abstract, table of contents, lists of tables and figures, and abbreviations as required by departmental guidelines.",
                True,
            ),
            (
                "Chapter One — Introduction",
                "Include the background to the study, statement of the problem, aim and objectives, research questions where applicable, significance, scope and limitations.",
                True,
            ),
            (
                "Chapter Two — Literature Review",
                "Present the conceptual, theoretical and empirical review, related works and the research gap addressed by the project.",
                True,
            ),
            (
                "Chapter Three — Methodology and System Analysis/Design",
                "Describe the research methodology, requirements analysis, system analysis, design models, architecture, tools and implementation approach as applicable.",
                True,
            ),
            (
                "Chapter Four — Implementation, Testing and Results",
                "Present implementation details, system interfaces, testing, results, evaluation and discussion.",
                True,
            ),
            (
                "Chapter Five — Summary, Conclusion and Recommendations",
                "Summarise the work, state the conclusions and provide recommendations and possible future improvements.",
                True,
            ),
            (
                "References",
                "Provide all cited sources using the referencing style required by the department.",
                True,
            ),
            (
                "Appendices",
                "Include supporting materials such as questionnaires, source-code extracts, additional diagrams, user guides or other supplementary material. This section may be omitted when it is not applicable.",
                False,
            ),
        ]
        sections = [
            ProjectReportSection(
                session=session,
                title=title,
                description=description,
                sequence=index,
                is_required=is_required,
                created_by=request.user,
                updated_by=request.user,
            )
            for index, (title, description, is_required) in enumerate(standard_sections, start=1)
        ]
        ProjectReportSection.objects.bulk_create(sections)
        output = self.get_serializer(
            ProjectReportSection.objects.filter(session=session).order_by("sequence"),
            many=True,
        )
        return Response(output.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        raise MethodNotAllowed(
            "DELETE",
            detail="Report sections are retained for academic records. Deactivate a section instead.",
        )


class ProjectReportSubmissionViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectReportSubmissionSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        queryset = ProjectReportSubmission.objects.select_related(
            "section__session",
            "student_enrollment__user",
            "student_enrollment__session",
            "supervisor_assignment__lecturer__user",
        ).prefetch_related(
            "revisions__uploaded_by",
            "reviews__reviewer",
            "reviews__revision",
        )
        filters = Q(pk__in=[])
        if user.has_role(RoleCode.STUDENT):
            filters |= Q(student_enrollment__user=user)
        if user.has_role(RoleCode.LECTURER):
            filters |= Q(
                student_enrollment__supervisor_assignments__lecturer__user=user,
                student_enrollment__supervisor_assignments__is_current=True,
                student_enrollment__supervisor_assignments__lecturer__is_active=True,
            ) | Q(reviews__reviewer=user)
        return queryset.filter(filters).distinct().order_by("section__sequence", "-submitted_at")

    def get_serializer_class(self):
        if self.action == "create":
            return ReportSubmissionUploadSerializer
        if self.action == "resubmit":
            return ReportRevisionUploadSerializer
        if self.action == "review":
            return ReportReviewActionSerializer
        return ProjectReportSubmissionSerializer

    def create(self, request, *args, **kwargs):
        if (
            not request.user.has_role(RoleCode.STUDENT)
            or request.user.has_role(RoleCode.PROJECT_COORDINATOR)
            or request.user.has_role(RoleCode.ADMINISTRATOR)
            or request.user.is_superuser
        ):
            raise PermissionDenied("Only students can submit project report sections.")
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        try:
            submission = submit_report_section(
                actor=request.user,
                section_id=values["section"].pk,
                uploaded_file=values["file"],
                submission_note=values.get("submission_note", ""),
            )
        except DjangoValidationError as exc:
            raise_api_validation_error(exc)
        output = ProjectReportSubmissionSerializer(
            submission,
            context=self.get_serializer_context(),
        )
        return Response(output.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def resubmit(self, request, pk=None):
        if (
            not request.user.has_role(RoleCode.STUDENT)
            or request.user.has_role(RoleCode.PROJECT_COORDINATOR)
            or request.user.has_role(RoleCode.ADMINISTRATOR)
            or request.user.is_superuser
        ):
            raise PermissionDenied("Only students can revise their project report sections.")
        submission_record = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        try:
            submission = resubmit_report_section(
                submission_id=submission_record.pk,
                actor=request.user,
                uploaded_file=values["file"],
                submission_note=values.get("submission_note", ""),
            )
        except DjangoValidationError as exc:
            raise_api_validation_error(exc)
        return Response(
            ProjectReportSubmissionSerializer(
                submission,
                context=self.get_serializer_context(),
            ).data
        )

    @action(detail=True, methods=["post"])
    def review(self, request, pk=None):
        if not request.user.has_role(RoleCode.LECTURER):
            raise PermissionDenied("Only the assigned supervisor can review project report sections.")
        submission_record = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        try:
            submission = review_report_section(
                submission_id=submission_record.pk,
                actor=request.user,
                decision=values["decision"],
                feedback=values.get("feedback", ""),
                annotation=values.get("annotation"),
            )
        except DjangoValidationError as exc:
            raise_api_validation_error(exc)
        return Response(
            ProjectReportSubmissionSerializer(
                submission,
                context=self.get_serializer_context(),
            ).data
        )

    @action(
        detail=True,
        methods=["get"],
        url_path=r"revisions/(?P<revision_id>[^/.]+)/download",
    )
    def download_revision(self, request, pk=None, revision_id=None):
        submission = self.get_object()
        revision = ProjectReportRevision.objects.filter(
            pk=revision_id,
            submission=submission,
        ).first()
        if revision is None:
            raise ValidationError("The requested document could not be found.")
        from .report_serializers import can_access_current_report
        if not can_access_current_report(submission, request.user) and not revision.reviews.filter(reviewer=request.user).exists():
            raise PermissionDenied("You cannot access this document version.")
        try:
            signed_url = create_report_download_url(
                revision.storage_path,
                download_filename=revision.original_filename,
            )
        except ReportStorageError:
            return Response(
                {"detail": "The document is temporarily unavailable for download."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response({"url": signed_url, "expires_in": 300})

    @action(detail=True, methods=["get"], url_path=r"reviews/(?P<review_id>[^/.]+)/download")
    def download_annotation(self, request, pk=None, review_id=None):
        submission = self.get_object()
        review = ProjectReportReview.objects.filter(pk=review_id, submission=submission).first()
        if not review or not review.annotation_path:
            raise ValidationError("The annotated document could not be found.")
        from .report_serializers import can_access_current_report
        if not can_access_current_report(submission, request.user) and review.reviewer_id != request.user.pk:
            raise PermissionDenied("You cannot access this annotated document.")
        try:
            url = create_report_download_url(review.annotation_path, download_filename=review.annotation_filename)
        except ReportStorageError:
            return Response({"detail": "The annotated document is temporarily unavailable."}, status=503)
        return Response({"url": url, "expires_in": 300})

    def destroy(self, request, *args, **kwargs):
        raise MethodNotAllowed("DELETE", detail="Submitted report records are retained for academic purposes.")
