from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.models import RoleCode

from .models import ProjectTopic, ProjectTopicStatus
from .serializers import (
    ProjectTopicReviewActionSerializer,
    ProjectTopicSerializer,
    ProjectTopicSubmissionSerializer,
    ProjectTopicSimilaritySerializer,
)
from .services import review_project_topic, resubmit_project_topic, submit_project_topic
from .similarity import SIMILARITY_THRESHOLD, analyse_topic_similarity


def raise_api_validation_error(exc):
    if isinstance(exc, DjangoValidationError):
        if hasattr(exc, "message_dict"):
            raise ValidationError(exc.message_dict)
        raise ValidationError(exc.messages)
    raise exc


class ProjectTopicViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectTopicSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]
    queryset = ProjectTopic.objects.select_related(
        "student_enrollment__user",
        "student_enrollment__session",
        "supervisor_assignment__lecturer__user",
    ).prefetch_related("revisions", "reviews__reviewer", "reviews__revision")

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()
        if user.is_superuser or user.has_role(RoleCode.ADMINISTRATOR) or user.has_role(RoleCode.PROJECT_COORDINATOR):
            return queryset
        role_filter = Q(pk__in=[])
        if user.has_role(RoleCode.LECTURER):
            role_filter |= Q(supervisor_assignment__lecturer__user=user)
        if user.has_role(RoleCode.STUDENT):
            role_filter |= Q(student_enrollment__user=user)
        return queryset.filter(role_filter).distinct()

    def get_serializer_class(self):
        if self.action in {"create", "resubmit"}:
            return ProjectTopicSubmissionSerializer
        if self.action == "review":
            return ProjectTopicReviewActionSerializer
        return ProjectTopicSerializer

    def create(self, request, *args, **kwargs):
        if not request.user.has_role(RoleCode.STUDENT):
            raise PermissionDenied("Only students can submit project topics.")
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            topic = submit_project_topic(actor=request.user, data=serializer.validated_data)
        except DjangoValidationError as exc:
            raise_api_validation_error(exc)
        transaction.on_commit(
            lambda topic_id=topic.pk: analyse_topic_similarity(topic_id)
        )
        output = ProjectTopicSerializer(topic, context=self.get_serializer_context())
        return Response(output.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"])
    def mine(self, request):
        if not request.user.has_role(RoleCode.STUDENT):
            raise PermissionDenied("This view is available to students.")
        topics = self.get_queryset().filter(student_enrollment__user=request.user)
        return Response(self.get_serializer(topics, many=True).data)

    @action(detail=False, methods=["get"], url_path="review-queue")
    def review_queue(self, request):
        if not request.user.has_role(RoleCode.LECTURER):
            raise PermissionDenied("This view is available to supervisors.")
        topics = self.get_queryset().filter(
            supervisor_assignment__lecturer__user=request.user,
            supervisor_assignment__is_current=True,
            status=ProjectTopicStatus.SUBMITTED,
            is_current=True,
        )
        return Response(self.get_serializer(topics, many=True).data)

    @action(detail=False, methods=["get"])
    def supervised(self, request):
        if not request.user.has_role(RoleCode.LECTURER):
            raise PermissionDenied("This view is available to supervisors.")
        topics = super().get_queryset().filter(
            Q(supervisor_assignment__lecturer__user=request.user)
            | Q(reviews__reviewer=request.user)
        ).distinct().order_by("-updated_at", "-submitted_at")
        return Response(self.get_serializer(topics, many=True).data)

    @action(detail=True, methods=["post"])
    def resubmit(self, request, pk=None):
        if not request.user.has_role(RoleCode.STUDENT):
            raise PermissionDenied("Only students can revise project topics.")
        topic_record = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            topic = resubmit_project_topic(
                topic_id=topic_record.pk,
                actor=request.user,
                data=serializer.validated_data,
            )
        except DjangoValidationError as exc:
            raise_api_validation_error(exc)
        transaction.on_commit(
            lambda topic_id=topic.pk: analyse_topic_similarity(topic_id)
        )
        return Response(ProjectTopicSerializer(topic, context=self.get_serializer_context()).data)

    def _require_current_supervisor(self, topic, user):
        assignment = topic.supervisor_assignment
        if (
            user.is_superuser
            or user.has_role(RoleCode.ADMINISTRATOR)
            or user.has_role(RoleCode.PROJECT_COORDINATOR)
            or not user.has_role(RoleCode.LECTURER)
            or not assignment.is_current
            or assignment.lecturer.user_id != user.id
        ):
            raise PermissionDenied("This information is available to the assigned supervisor only.")

    def _similarity_report_response(self, revision):
        from .models import ProjectTopicSimilarity

        matches = ProjectTopicSimilarity.objects.filter(
            source_revision=revision
        ).select_related(
            "matched_revision__topic__student_enrollment__session"
        )
        return Response(
            {
                "status": revision.similarity_status,
                "analysed_at": revision.similarity_analyzed_at,
                "threshold_percent": round(SIMILARITY_THRESHOLD * 100),
                "matches": ProjectTopicSimilaritySerializer(matches, many=True).data,
            }
        )

    @action(detail=True, methods=["get"], url_path="similarity-report")
    def similarity_report(self, request, pk=None):
        if (
            request.user.is_superuser
            or request.user.has_role(RoleCode.ADMINISTRATOR)
            or request.user.has_role(RoleCode.PROJECT_COORDINATOR)
            or not request.user.has_role(RoleCode.LECTURER)
        ):
            raise PermissionDenied("This information is available to supervisors only.")
        topic = self.get_object()
        self._require_current_supervisor(topic, request.user)
        revision = topic.revisions.order_by("-revision_number").first()
        if revision is None:
            raise ValidationError("The proposal history could not be found.")
        return self._similarity_report_response(revision)

    @action(detail=True, methods=["post"], url_path="run-similarity")
    def run_similarity(self, request, pk=None):
        if (
            request.user.is_superuser
            or request.user.has_role(RoleCode.ADMINISTRATOR)
            or request.user.has_role(RoleCode.PROJECT_COORDINATOR)
            or not request.user.has_role(RoleCode.LECTURER)
        ):
            raise PermissionDenied("This action is available to supervisors only.")
        topic = self.get_object()
        self._require_current_supervisor(topic, request.user)
        analyse_topic_similarity(topic.pk, force=True)
        revision = topic.revisions.order_by("-revision_number").first()
        return self._similarity_report_response(revision)

    @action(detail=True, methods=["post"])
    def review(self, request, pk=None):
        if not request.user.has_role(RoleCode.LECTURER):
            raise PermissionDenied("Only the assigned supervisor can review project topics.")
        topic_record = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            topic = review_project_topic(
                topic_id=topic_record.pk,
                actor=request.user,
                decision=serializer.validated_data["decision"],
                feedback=serializer.validated_data.get("feedback", ""),
            )
        except DjangoValidationError as exc:
            raise_api_validation_error(exc)
        return Response(ProjectTopicSerializer(topic, context=self.get_serializer_context()).data)
