from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed, PermissionDenied, ValidationError
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response

from apps.accounts.models import RoleCode
from apps.academics.models import StudentEnrollment, SupervisorAssignment

from .models import ProjectMilestone, ProjectProgressReport
from .progress_serializers import (
    ProjectMilestoneSerializer,
    ProjectProgressReportSerializer,
    ProjectProgressReportSubmissionSerializer,
    ProjectProgressRevisionSubmissionSerializer,
    ProjectProgressReviewActionSerializer,
)
from .progress_services import (
    resubmit_progress_report,
    review_progress_report,
    submit_progress_report,
)


class IsProjectCoordinator(BasePermission):
    message = "Only the Project Coordinator can manage project milestones."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.has_role(RoleCode.PROJECT_COORDINATOR))


def raise_api_validation_error(exc):
    if isinstance(exc, DjangoValidationError):
        if hasattr(exc, "message_dict"):
            raise ValidationError(exc.message_dict)
        raise ValidationError(exc.messages)
    raise exc


class ProjectMilestoneViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectMilestoneSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "put", "patch", "head", "options"]

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update"}:
            return [IsProjectCoordinator()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        queryset = ProjectMilestone.objects.select_related("session", "created_by", "updated_by")
        if (
            user.is_superuser
            or user.has_role(RoleCode.ADMINISTRATOR)
            or user.has_role(RoleCode.PROJECT_COORDINATOR)
        ):
            return queryset

        session_ids = set()
        if user.has_role(RoleCode.STUDENT):
            session_ids.update(
                StudentEnrollment.objects.filter(
                    user=user,
                    verification_status__in=["auto_verified", "manually_approved"],
                ).values_list("session_id", flat=True)
            )
        if user.has_role(RoleCode.LECTURER):
            session_ids.update(
                SupervisorAssignment.objects.filter(
                    lecturer__user=user
                ).values_list("student_enrollment__session_id", flat=True)
            )
        if not session_ids:
            return queryset.none()
        return queryset.filter(session_id__in=session_ids)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def destroy(self, request, *args, **kwargs):
        raise MethodNotAllowed("DELETE", detail="Milestones are retained for historical progress records. Deactivate a milestone instead.")


class ProjectProgressReportViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectProgressReportSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        queryset = ProjectProgressReport.objects.select_related(
            "milestone__session",
            "student_enrollment__user",
            "student_enrollment__session",
            "supervisor_assignment__lecturer__user",
        ).prefetch_related(
            "revisions__submitted_by",
            "reviews__reviewer",
            "reviews__revision",
        )

        if (
            user.is_superuser
            or user.has_role(RoleCode.ADMINISTRATOR)
            or user.has_role(RoleCode.PROJECT_COORDINATOR)
        ):
            return queryset.none()

        filters = Q(pk__in=[])
        if user.has_role(RoleCode.STUDENT):
            filters |= Q(student_enrollment__user=user)
        if user.has_role(RoleCode.LECTURER):
            filters |= Q(
                student_enrollment__supervisor_assignments__lecturer__user=user,
                student_enrollment__supervisor_assignments__is_current=True,
            ) | Q(reviews__reviewer=user)
        return queryset.filter(filters).distinct().order_by("-submitted_at")

    def get_serializer_class(self):
        if self.action == "create":
            return ProjectProgressReportSubmissionSerializer
        if self.action == "resubmit":
            return ProjectProgressRevisionSubmissionSerializer
        if self.action == "review":
            return ProjectProgressReviewActionSerializer
        return ProjectProgressReportSerializer

    def create(self, request, *args, **kwargs):
        if (
            not request.user.has_role(RoleCode.STUDENT)
            or request.user.has_role(RoleCode.PROJECT_COORDINATOR)
            or request.user.has_role(RoleCode.ADMINISTRATOR)
            or request.user.is_superuser
        ):
            raise PermissionDenied("Only students can submit progress reports.")
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        try:
            report = submit_progress_report(
                actor=request.user,
                milestone_id=values["milestone"].pk,
                data=values,
            )
        except DjangoValidationError as exc:
            raise_api_validation_error(exc)
        output = ProjectProgressReportSerializer(
            report,
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
            raise PermissionDenied("Only students can revise progress reports.")
        report_record = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            report = resubmit_progress_report(
                report_id=report_record.pk,
                actor=request.user,
                data=serializer.validated_data,
            )
        except DjangoValidationError as exc:
            raise_api_validation_error(exc)
        return Response(
            ProjectProgressReportSerializer(report, context=self.get_serializer_context()).data
        )

    @action(detail=True, methods=["post"])
    def review(self, request, pk=None):
        if not request.user.has_role(RoleCode.LECTURER):
            raise PermissionDenied("Only the assigned supervisor can review progress reports.")
        report_record = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        try:
            report = review_progress_report(
                report_id=report_record.pk,
                actor=request.user,
                decision=values["decision"],
                assessment=values["assessment"],
                feedback=values.get("feedback", ""),
            )
        except DjangoValidationError as exc:
            raise_api_validation_error(exc)
        return Response(
            ProjectProgressReportSerializer(report, context=self.get_serializer_context()).data
        )
