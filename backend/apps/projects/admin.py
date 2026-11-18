from django.contrib import admin

from .models import ProjectTopic, ProjectTopicReview, ProjectTopicRevision


class ProjectTopicRevisionInline(admin.TabularInline):
    model = ProjectTopicRevision
    extra = 0
    can_delete = False
    readonly_fields = (
        "revision_number",
        "title",
        "submitted_by",
        "submitted_at",
    )


class ProjectTopicReviewInline(admin.TabularInline):
    model = ProjectTopicReview
    extra = 0
    can_delete = False
    readonly_fields = (
        "revision",
        "supervisor_assignment",
        "reviewer",
        "decision",
        "feedback",
        "reviewed_at",
    )


@admin.register(ProjectTopic)
class ProjectTopicAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "student_enrollment",
        "supervisor_assignment",
        "status",
        "is_current",
        "submitted_at",
    )
    list_filter = ("status", "is_current", "student_enrollment__session")
    search_fields = (
        "title",
        "student_enrollment__matric_number",
        "student_enrollment__user__first_name",
        "student_enrollment__user__last_name",
    )
    readonly_fields = ("submitted_at", "reviewed_at", "created_at", "updated_at")
    inlines = (ProjectTopicRevisionInline, ProjectTopicReviewInline)

    def has_delete_permission(self, request, obj=None):
        return False
