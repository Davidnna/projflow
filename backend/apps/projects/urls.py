from rest_framework.routers import DefaultRouter

from .progress_views import ProjectMilestoneViewSet, ProjectProgressReportViewSet
from .views import ProjectTopicViewSet

router = DefaultRouter()
router.register("topics", ProjectTopicViewSet, basename="project-topic")
router.register("milestones", ProjectMilestoneViewSet, basename="project-milestone")
router.register("progress-reports", ProjectProgressReportViewSet, basename="project-progress-report")

urlpatterns = router.urls
