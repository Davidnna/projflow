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

from .models import (
    ProjectMilestone,
    ProjectProgressReport,
    ProjectProgressReview,
    ProjectProgressRevision,
)


@admin.register(ProjectMilestone)
class ProjectMilestoneAdmin(admin.ModelAdmin):
    list_display = ("title", "session", "sequence", "due_date", "is_active")
    list_filter = ("session", "is_active")
    search_fields = ("title", "description", "session__name")
    readonly_fields = ("created_at", "updated_at")

    def has_delete_permission(self, request, obj=None):
        return False


class ProjectProgressRevisionInline(admin.TabularInline):
    model = ProjectProgressRevision
    extra = 0
    can_delete = False
    readonly_fields = (
        "revision_number",
        "completed_activities",
        "challenges",
        "next_steps",
        "submitted_by",
        "submitted_at",
    )


class ProjectProgressReviewInline(admin.TabularInline):
    model = ProjectProgressReview
    extra = 0
    can_delete = False
    readonly_fields = (
        "revision",
        "supervisor_assignment",
        "reviewer",
        "decision",
        "assessment",
        "feedback",
        "reviewed_at",
    )


@admin.register(ProjectProgressReport)
class ProjectProgressReportAdmin(admin.ModelAdmin):
    list_display = (
        "milestone",
        "student_enrollment",
        "supervisor_assignment",
        "status",
        "submitted_at",
    )
    list_filter = ("status", "milestone__session", "milestone")
    search_fields = (
        "student_enrollment__matric_number",
        "student_enrollment__user__first_name",
        "student_enrollment__user__last_name",
        "milestone__title",
    )
    readonly_fields = ("submitted_at", "reviewed_at", "created_at", "updated_at")
    inlines = (ProjectProgressRevisionInline, ProjectProgressReviewInline)

    def has_delete_permission(self, request, obj=None):
        return False
