from django.db import DatabaseError, connection
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    return Response({"status": "ok"}, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([AllowAny])
def readiness_check(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except DatabaseError:
        return Response(
            {"status": "not_ready"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    return Response({"status": "ready"}, status=status.HTTP_200_OK)
