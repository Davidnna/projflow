from rest_framework.permissions import BasePermission

from apps.accounts.models import RoleCode


class IsCoordinatorOrAdministrator(BasePermission):
    message = "Only the Project Coordinator or Administrator can perform this action."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (
                user.is_superuser
                or user.has_role(RoleCode.ADMINISTRATOR)
                or user.has_role(RoleCode.PROJECT_COORDINATOR)
            )
        )


class IsLecturerOrCoordinator(BasePermission):
    message = "This action requires a lecturer or departmental coordinator account."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (
                user.is_superuser
                or user.has_role(RoleCode.ADMINISTRATOR)
                or user.has_role(RoleCode.PROJECT_COORDINATOR)
                or user.has_role(RoleCode.LECTURER)
            )
        )
