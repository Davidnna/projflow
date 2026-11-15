from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AcademicSessionViewSet,
    LecturerProfileViewSet,
    LecturerWorkloadView,
    RosterImportBatchViewSet,
    RosterImportPreviewView,
    StudentEnrollmentViewSet,
    StudentRosterRecordViewSet,
    SupervisorAssignmentViewSet,
)

router = DefaultRouter()
router.register("sessions", AcademicSessionViewSet, basename="academic-session")
router.register("roster", StudentRosterRecordViewSet, basename="student-roster")
router.register("roster-imports", RosterImportBatchViewSet, basename="roster-import")
router.register("enrollments", StudentEnrollmentViewSet, basename="student-enrollment")
router.register("lecturers", LecturerProfileViewSet, basename="lecturer-profile")
router.register("supervisor-assignments", SupervisorAssignmentViewSet, basename="supervisor-assignment")

urlpatterns = [
    path("roster-imports/preview/", RosterImportPreviewView.as_view(), name="roster-import-preview"),
    path("lecturer-workloads/", LecturerWorkloadView.as_view(), name="lecturer-workloads"),
    path("", include(router.urls)),
]
