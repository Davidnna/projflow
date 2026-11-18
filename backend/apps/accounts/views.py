import secrets

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import Role, RoleCode, UserRole
from .serializers import (
    CoordinatorAccessUpdateSerializer,
    InitialAdministratorSetupSerializer,
    ProjFlowTokenObtainPairSerializer,
)

User = get_user_model()


class ProjFlowTokenObtainPairView(TokenObtainPairView):
    serializer_class = ProjFlowTokenObtainPairSerializer


class InitialAdministratorSetupThrottle(AnonRateThrottle):
    scope = "initial_admin_setup"


def initial_administrator_exists():
    administrator_role = Role.objects.filter(code=RoleCode.ADMINISTRATOR).first()
    return User.objects.filter(is_superuser=True).exists() or bool(
        administrator_role
        and UserRole.objects.filter(role=administrator_role).exists()
    )


def initial_administrator_setup_enabled():
    setup_token = getattr(settings, "PROJFLOW_INITIAL_ADMIN_SETUP_TOKEN", "")
    return len(setup_token) >= 32 and not initial_administrator_exists()


class InitialAdministratorSetupView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [InitialAdministratorSetupThrottle]

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Cache-Control"] = "no-store"
        return response

    def get(self, request):
        return Response(
            {"setup_available": initial_administrator_setup_enabled()},
            status=status.HTTP_200_OK,
        )

    def post(self, request):
        if initial_administrator_exists():
            return Response(
                {"detail": "Initial Administrator setup has already been completed."},
                status=status.HTTP_410_GONE,
            )

        configured_token = getattr(
            settings,
            "PROJFLOW_INITIAL_ADMIN_SETUP_TOKEN",
            "",
        )
        if len(configured_token) < 32:
            return Response(
                {"detail": "Initial Administrator setup is not enabled."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        supplied_token = request.data.get("setup_token", "")
        if not isinstance(supplied_token, str) or not secrets.compare_digest(
            supplied_token.encode("utf-8"),
            configured_token.encode("utf-8"),
        ):
            return Response(
                {"detail": "The setup secret is invalid."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = InitialAdministratorSetupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data

        try:
            with transaction.atomic():
                administrator_role = (
                    Role.objects.select_for_update()
                    .filter(code=RoleCode.ADMINISTRATOR)
                    .first()
                )
                if administrator_role is None:
                    return Response(
                        {"detail": "System roles are not initialised. Contact the system maintainer."},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE,
                    )

                if initial_administrator_exists():
                    return Response(
                        {"detail": "Initial Administrator setup has already been completed."},
                        status=status.HTTP_410_GONE,
                    )

                user = User.objects.create_superuser(
                    email=values["email"],
                    password=values["password"],
                    first_name=values["first_name"].strip(),
                    last_name=values["last_name"].strip(),
                )
        except IntegrityError:
            return Response(
                {"detail": "An account with these details already exists. Refresh the page and try again."},
                status=status.HTTP_409_CONFLICT,
            )

        response = Response(
            {
                "message": "The initial Administrator account has been created.",
                "email": user.email,
            },
            status=status.HTTP_201_CREATED,
        )
        return response


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


class CoordinatorAccessView(APIView):
    permission_classes = [IsAuthenticated]

    def ensure_administrator(self, user):
        if not (user.is_superuser or user.has_role(RoleCode.ADMINISTRATOR)):
            raise PermissionDenied("Only an Administrator can manage coordinator access.")

    def eligible_accounts(self):
        eligible_roles = [
            RoleCode.ADMINISTRATOR,
            RoleCode.LECTURER,
            RoleCode.PROJECT_COORDINATOR,
        ]
        return (
            User.objects.filter(
                is_active=True,
            )
            .filter(role_assignments__role__code__in=eligible_roles)
            .distinct()
            .prefetch_related("role_assignments__role")
            .order_by("first_name", "last_name", "email")
        )

    def serialize_account(self, user):
        roles = list(
            user.role_assignments.select_related("role").values_list(
                "role__code", flat=True
            )
        )
        return {
            "id": str(user.pk),
            "name": user.get_full_name() or user.email,
            "email": user.email,
            "roles": roles,
            "is_active": user.is_active,
            "has_coordinator_access": RoleCode.PROJECT_COORDINATOR in roles,
            "can_receive_coordinator_access": bool(
                RoleCode.ADMINISTRATOR in roles or RoleCode.LECTURER in roles
            ),
        }

    def get(self, request):
        self.ensure_administrator(request.user)
        return Response([
            self.serialize_account(user)
            for user in self.eligible_accounts()
        ])

    def post(self, request):
        self.ensure_administrator(request.user)
        serializer = CoordinatorAccessUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data

        with transaction.atomic():
            target = User.objects.filter(
                pk=values["user_id"],
                is_active=True,
            ).first()
            if target is None or not (
                target.has_role(RoleCode.ADMINISTRATOR)
                or target.has_role(RoleCode.LECTURER)
                or target.has_role(RoleCode.PROJECT_COORDINATOR)
            ):
                raise NotFound("The selected staff account could not be found.")

            coordinator_role = Role.objects.filter(
                code=RoleCode.PROJECT_COORDINATOR
            ).first()
            if coordinator_role is None:
                raise ValidationError("Coordinator access is currently unavailable.")

            if values["enabled"]:
                if not (
                    target.has_role(RoleCode.ADMINISTRATOR)
                    or target.has_role(RoleCode.LECTURER)
                ):
                    raise ValidationError(
                        "Coordinator access can only be granted to an Administrator or Lecturer account."
                    )
                UserRole.objects.get_or_create(
                    user=target,
                    role=coordinator_role,
                    defaults={"assigned_by": request.user},
                )
                message = "Project Coordinator access granted."
            else:
                UserRole.objects.filter(
                    user=target,
                    role=coordinator_role,
                ).delete()
                message = "Project Coordinator access removed."

        target.refresh_from_db()
        return Response({
            "message": message,
            "account": self.serialize_account(target),
        })
