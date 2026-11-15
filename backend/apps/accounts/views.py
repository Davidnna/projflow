from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import ProjFlowTokenObtainPairSerializer


class ProjFlowTokenObtainPairView(TokenObtainPairView):
    serializer_class = ProjFlowTokenObtainPairSerializer


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            raise ValidationError({"refresh": "A refresh token is required."})
        try:
            token = RefreshToken(refresh_token)
            if str(token.get("user_id")) != str(request.user.pk):
                raise PermissionDenied("The refresh token does not belong to the authenticated user.")
            token.blacklist()
        except TokenError as exc:
            raise ValidationError({"refresh": "The refresh token is invalid or expired."}) from exc
        return Response(status=status.HTTP_205_RESET_CONTENT)
