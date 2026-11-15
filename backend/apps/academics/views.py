from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Count, Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed, PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import RoleCode

from .importers import commit_roster_import, preview_roster_import
from .models import (
    AcademicSession,
    AcademicSessionStatus,
    LecturerProfile,
    RosterImportBatch,
    StudentEnrollment,
    StudentRosterRecord,
    SupervisorAssignment,
)
from .permissions import IsCoordinatorOrAdministrator
from .serializers import (
    AcademicSessionSerializer,
    LecturerProfileSerializer,
    RosterImportBatchSerializer,
    RosterImportPreviewSerializer,
    StudentEnrollmentReviewSerializer,
    StudentEnrollmentSerializer,
    StudentRegistrationSerializer,
    StudentRegistrationStatusSerializer,
    StudentRosterRecordSerializer,
    SupervisorAssignmentCreateSerializer,
    SupervisorAssignmentSerializer,
    SupervisorReassignmentSerializer,
)
from .services import (
    activate_academic_session,
    assign_supervisor,
    close_academic_session,
    reassign_supervisor,
    review_student_enrollment,
)


def is_coordinator_or_administrator(user):
    return bool(
        user.is_authenticated
        and (
            user.is_superuser
            or user.has_role(RoleCode.ADMINISTRATOR)
            or user.has_role(RoleCode.PROJECT_COORDINATOR)
        )
    )


def raise_api_validation_error(exc):
    if isinstance(exc, DjangoValidationError):
        if hasattr(exc, "message_dict"):
            raise ValidationError(exc.message_dict)
        raise ValidationError(exc.messages)
    raise exc


class AcademicSessionViewSet(viewsets.ModelViewSet):
    queryset = AcademicSession.objects.select_related("created_by", "updated_by").all()
    serializer_class = AcademicSessionSerializer

    def get_permissions(self):
        if self.action in {"list", "retrieve"}:
            return [IsAuthenticated()]
        return [IsCoordinatorOrAdministrator()]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def destroy(self, request, *args, **kwargs):
        raise MethodNotAllowed("DELETE", detail="Academic sessions are retained for historical records.")

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        session_record = self.get_object()
        try:
            session = activate_academic_session(session_record.pk, request.user)
        except DjangoValidationError as exc:
            raise_api_validation_error(exc)
        return Response(self.get_serializer(session).data)

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        session_record = self.get_object()
        try:
            session = close_academic_session(session_record.pk, request.user)
        except DjangoValidationError as exc:
            raise_api_validation_error(exc)
        return Response(self.get_serializer(session).data)


class StudentRosterRecordViewSet(viewsets.ModelViewSet):
    queryset = StudentRosterRecord.objects.select_related("session", "created_by").all()
    serializer_class = StudentRosterRecordSerializer
    permission_classes = [IsCoordinatorOrAdministrator]
    parser_classes = [JSONParser]

    def perform_create(self, serializer):
        serializer.save(
            source="manual",
            created_by=self.request.user,
            updated_by=self.request.user,
        )

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def destroy(self, request, *args, **kwargs):
        raise MethodNotAllowed("DELETE", detail="Student roster records are retained for audit and historical reference.")


class RosterImportPreviewView(APIView):
    permission_classes = [IsCoordinatorOrAdministrator]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = RosterImportPreviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            batch = preview_roster_import(
                session=serializer.validated_data["session"],
                uploaded_file=serializer.validated_data["file"],
                actor=request.user,
            )
        except DjangoValidationError as exc:
            raise_api_validation_error(exc)
        return Response(
            RosterImportBatchSerializer(batch).data,
            status=status.HTTP_201_CREATED,
        )


class RosterImportBatchViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = RosterImportBatch.objects.select_related("session", "uploaded_by").prefetch_related("rows")
    serializer_class = RosterImportBatchSerializer
    permission_classes = [IsCoordinatorOrAdministrator]

    @action(detail=True, methods=["post"])
    def commit(self, request, pk=None):
        batch_record = self.get_object()
        try:
            batch = commit_roster_import(batch_id=batch_record.pk, actor=request.user)
        except DjangoValidationError as exc:
            raise_api_validation_error(exc)
        return Response(self.get_serializer(batch).data)


class StudentRegistrationView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = StudentRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user, enrollment = serializer.save()
        except DjangoValidationError as exc:
            raise_api_validation_error(exc)
        return Response(
            {
                "message": "Registration submitted successfully.",
                "user_id": str(user.pk),
                "email": user.email,
                "enrollment": StudentRegistrationStatusSerializer(enrollment).data,
            },
            status=status.HTTP_201_CREATED,
        )


class StudentEnrollmentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = StudentEnrollmentSerializer
    permission_classes = [IsAuthenticated]
    queryset = StudentEnrollment.objects.select_related(
        "user",
        "session",
        "roster_record",
        "reviewed_by",
    ).all()

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()
        if is_coordinator_or_administrator(user):
            return queryset
        role_filter = Q(pk__in=[])
        if user.has_role(RoleCode.LECTURER):
            role_filter |= Q(
                supervisor_assignments__lecturer__user=user,
                supervisor_assignments__is_current=True,
            )
        if user.has_role(RoleCode.STUDENT):
            role_filter |= Q(user=user)
        return queryset.filter(role_filter).distinct()

    @action(detail=False, methods=["get"])
    def mine(self, request):
        enrollment = self.get_queryset().filter(user=request.user).order_by("-created_at").first()
        if enrollment is None:
            return Response({"detail": "No student registration was found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(StudentRegistrationStatusSerializer(enrollment).data)

    @action(detail=True, methods=["post"])
    def review(self, request, pk=None):
        if not is_coordinator_or_administrator(request.user):
            raise PermissionDenied("Only the Project Coordinator or Administrator can review registrations.")
        serializer = StudentEnrollmentReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        enrollment_record = self.get_object()
        try:
            enrollment = review_student_enrollment(
                enrollment_id=enrollment_record.pk,
                actor=request.user,
                decision=serializer.validated_data["decision"],
                notes=serializer.validated_data.get("notes", ""),
            )
        except DjangoValidationError as exc:
            raise_api_validation_error(exc)
        return Response(StudentEnrollmentSerializer(enrollment).data)


class LecturerProfileViewSet(viewsets.ModelViewSet):
    queryset = LecturerProfile.objects.select_related("user").all()
    serializer_class = LecturerProfileSerializer

    def get_permissions(self):
        if self.action in {"list", "retrieve"}:
            return [IsAuthenticated()]
        return [IsCoordinatorOrAdministrator()]

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()
        if is_coordinator_or_administrator(user):
            return queryset
        if user.has_role(RoleCode.LECTURER):
            return queryset.filter(user=user)
        return queryset.none()

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])


class SupervisorAssignmentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SupervisorAssignment.objects.select_related(
        "student_enrollment__user",
        "student_enrollment__session",
        "lecturer__user",
        "assigned_by",
        "ended_by",
    ).all()
    serializer_class = SupervisorAssignmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()
        if is_coordinator_or_administrator(user):
            return queryset
        role_filter = Q(pk__in=[])
        if user.has_role(RoleCode.LECTURER):
            role_filter |= Q(lecturer__user=user)
        if user.has_role(RoleCode.STUDENT):
            role_filter |= Q(student_enrollment__user=user)
        return queryset.filter(role_filter).distinct()

    @action(detail=False, methods=["post"])
    def assign(self, request):
        if not is_coordinator_or_administrator(request.user):
            raise PermissionDenied("Only the Project Coordinator or Administrator can assign supervisors.")
        serializer = SupervisorAssignmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        enrollment = StudentEnrollment.objects.filter(pk=serializer.validated_data["student_enrollment"]).first()
        lecturer = LecturerProfile.objects.filter(pk=serializer.validated_data["lecturer"]).first()
        if enrollment is None or lecturer is None:
            raise ValidationError("The selected student registration or lecturer profile does not exist.")
        try:
            assignment = assign_supervisor(
                enrollment_id=enrollment.pk,
                lecturer_id=lecturer.pk,
                actor=request.user,
            )
        except DjangoValidationError as exc:
            raise_api_validation_error(exc)
        return Response(
            self.get_serializer(assignment).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def reassign(self, request, pk=None):
        if not is_coordinator_or_administrator(request.user):
            raise PermissionDenied("Only the Project Coordinator or Administrator can reassign supervisors.")
        assignment_record = self.get_object()
        serializer = SupervisorReassignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        lecturer = LecturerProfile.objects.filter(pk=serializer.validated_data["lecturer"]).first()
        if lecturer is None:
            raise ValidationError("The selected lecturer profile does not exist.")
        try:
            assignment = reassign_supervisor(
                assignment_id=assignment_record.pk,
                lecturer_id=lecturer.pk,
                actor=request.user,
                reason=serializer.validated_data["reason"],
            )
        except DjangoValidationError as exc:
            raise_api_validation_error(exc)
        return Response(self.get_serializer(assignment).data, status=status.HTTP_201_CREATED)


class LecturerWorkloadView(APIView):
    permission_classes = [IsCoordinatorOrAdministrator]

    def get(self, request):
        lecturers = (
            LecturerProfile.objects.filter(is_active=True, user__is_active=True)
            .select_related("user")
            .annotate(
                active_supervisee_count=Count(
                    "supervisor_assignments",
                    filter=Q(
                        supervisor_assignments__is_current=True,
                        supervisor_assignments__student_enrollment__session__status=AcademicSessionStatus.ACTIVE,
                    ),
                )
            )
            .order_by("active_supervisee_count", "user__last_name", "user__first_name")
        )
        data = [
            {
                "lecturer_id": str(lecturer.pk),
                "name": lecturer.user.get_full_name(),
                "email": lecturer.user.email,
                "staff_number": lecturer.staff_number,
                "designation": lecturer.designation,
                "active_supervisee_count": lecturer.active_supervisee_count,
            }
            for lecturer in lecturers
        ]
        return Response(data)
