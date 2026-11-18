from rest_framework.routers import DefaultRouter

from .views import ProjectTopicViewSet

router = DefaultRouter()
router.register("topics", ProjectTopicViewSet, basename="project-topic")

urlpatterns = router.urls
