from django.urls import path
from .lifecycle_views import CompletionWorkspaceView, FinalDocumentDownloadView, NotificationWorkspaceView
from rest_framework.routers import DefaultRouter

from .progress_views import ProjectMilestoneViewSet, ProjectProgressReportViewSet
from .report_views import ProjectReportSectionViewSet, ProjectReportSubmissionViewSet
from .views import ProjectTopicViewSet

router = DefaultRouter()
router.register("topics", ProjectTopicViewSet, basename="project-topic")
router.register("milestones", ProjectMilestoneViewSet, basename="project-milestone")
router.register("progress-reports", ProjectProgressReportViewSet, basename="project-progress-report")
router.register("report-sections", ProjectReportSectionViewSet, basename="project-report-section")
router.register("report-submissions", ProjectReportSubmissionViewSet, basename="project-report-submission")

urlpatterns = [
    path("completion/", CompletionWorkspaceView.as_view(), name="project-completion"),
    path("final-documents/<uuid:document_id>/download/", FinalDocumentDownloadView.as_view(), name="final-document-download"),
    path("notifications/", NotificationWorkspaceView.as_view(), name="project-notifications"),
] + router.urls
