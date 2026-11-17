from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from apps.academics.views import StudentRegistrationView

from .views import (
    InitialAdministratorSetupView,
    LogoutView,
    ProjFlowTokenObtainPairView,
)

urlpatterns = [
    path("register/", StudentRegistrationView.as_view(), name="student-registration"),
    path(
        "initial-admin/",
        InitialAdministratorSetupView.as_view(),
        name="initial-administrator-setup",
    ),
    path("token/", ProjFlowTokenObtainPairView.as_view(), name="token-obtain-pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("logout/", LogoutView.as_view(), name="token-logout"),
]
