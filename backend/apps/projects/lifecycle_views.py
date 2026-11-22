from collections.abc import Mapping

from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import RoleCode

from .lifecycle import CATEGORIES, available_sessions, coordinator, examiner, get_row, perform_action, session_data, supervisor
from .models import FinalReportVersion, NotificationPreference, ProjectNotification
from .report_files import ReportStorageError, create_report_download_url


class CompletionWorkspaceView(APIView):
    def get(self, request):
        sessions = available_sessions(request.user)
        selected = request.query_params.get("session")
        if selected:
            selected = serializers.UUIDField().run_validation(selected)
            session = sessions.filter(pk=selected).first()
            if session is None:
                raise NotFound("Academic session unavailable.")
        else:
            session = sessions.filter(status="active").first() or sessions.first()
        return Response({"sessions": [{"id": str(s.pk), "name": s.name, "status": s.status} for s in sessions], "workspace": session_data(request.user, session) if session else None})

    def post(self, request):
        try:
            result = perform_action(request.user, request.data, request.FILES.get("file"))
        except DjangoValidationError as exc:
            raise ValidationError({"detail": " ".join(exc.messages)}) from exc
        return Response(result)


class FinalDocumentDownloadView(APIView):
    def get(self, request, document_id):
        doc = get_row(FinalReportVersion, document_id)
        user = request.user
        project = doc.project
        if not ((project.enrollment.user_id == user.pk and user.has_role(RoleCode.STUDENT)) or coordinator(user) or supervisor(user, project.enrollment) or examiner(user, project)):
            raise NotFound("Document unavailable.")
        try:
            url = create_report_download_url(doc.storage_path, download_filename=doc.original_filename)
        except ReportStorageError:
            return Response({"detail": "The document is temporarily unavailable."}, status=503)
        return Response({"url": url, "expires_in": 300})


class NotificationWorkspaceView(APIView):
    def get(self, request):
        preferences, _ = NotificationPreference.objects.get_or_create(user=request.user)
        categories = {c: {"in_app": preferences.categories.get(c, {}).get("in_app", True), "email": preferences.categories.get(c, {}).get("email", False)} for c in CATEGORIES}
        notifications = ProjectNotification.objects.filter(recipient=request.user).order_by("-created_at")
        return Response({"preferences": categories, "unread": notifications.filter(read_at__isnull=True).count(), "notifications": list(notifications.values("id", "category", "message", "read_at", "created_at")[:100])})

    def post(self, request):
        if not isinstance(request.data, Mapping):
            raise ValidationError("Provide a valid request object.")
        if request.data.get("action") == "mark_read":
            queryset = ProjectNotification.objects.filter(recipient=request.user, read_at__isnull=True)
            if request.data.get("id"):
                queryset = queryset.filter(pk=serializers.UUIDField().run_validation(request.data["id"]))
            queryset.update(read_at=timezone.now())
        elif request.data.get("action") == "preferences":
            raw = request.data.get("preferences")
            if not isinstance(raw, dict) or set(raw) != set(CATEGORIES):
                raise ValidationError("Provide notification preferences for each category.")
            preferences = {}
            for category, value in raw.items():
                if not isinstance(value, dict) or set(value) != {"in_app", "email"} or not all(isinstance(v, bool) for v in value.values()):
                    raise ValidationError("Notification preferences must be boolean values.")
                preferences[category] = value
            NotificationPreference.objects.update_or_create(user=request.user, defaults={"categories": preferences})
        else:
            raise ValidationError("Unknown notification action.")
        return self.get(request)
