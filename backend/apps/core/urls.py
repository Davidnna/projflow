from django.urls import path
from . import views

urlpatterns = [
    path("health/", views.health_check, name="api-health"),
    path("ready/", views.readiness_check, name="api-readiness"),
]
