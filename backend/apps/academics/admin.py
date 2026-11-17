from django.contrib import admin

from .models import (
    AcademicSession,
    LecturerProfile,
    RosterImportBatch,
    RosterImportRow,
    StudentEnrollment,
    StudentRosterRecord,
    SupervisorAssignment,
)


@admin.register(AcademicSession)
class AcademicSessionAdmin(admin.ModelAdmin):
    list_display = ("name", "status", "created_at")
    exclude = ("start_date", "end_date")
    list_filter = ("status",)
    search_fields = ("name",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(StudentRosterRecord)
class StudentRosterRecordAdmin(admin.ModelAdmin):
    list_display = (
        "matric_number",
        "last_name",
        "first_name",
        "session",
        "is_eligible",
        "source",
    )
    list_filter = ("session", "is_eligible", "source")
    search_fields = ("matric_number", "first_name", "last_name", "other_names")
    readonly_fields = ("created_at", "updated_at")


class RosterImportRowInline(admin.TabularInline):
    model = RosterImportRow
    extra = 0
    can_delete = False
    readonly_fields = (
        "row_number",
        "matric_number",
        "first_name",
        "last_name",
        "status",
        "errors",
    )


@admin.register(RosterImportBatch)
class RosterImportBatchAdmin(admin.ModelAdmin):
    list_display = (
        "original_file_name",
        "session",
        "status",
        "total_rows",
        "imported_rows",
        "uploaded_by",
        "created_at",
    )
    list_filter = ("status", "session")
    readonly_fields = (
        "original_file_name",
        "session",
        "status",
        "total_rows",
        "valid_rows",
        "invalid_rows",
        "duplicate_rows",
        "imported_rows",
        "uploaded_by",
        "created_at",
        "committed_at",
    )
    inlines = (RosterImportRowInline,)


@admin.register(StudentEnrollment)
class StudentEnrollmentAdmin(admin.ModelAdmin):
    list_display = (
        "matric_number",
        "user",
        "session",
        "verification_status",
        "verification_method",
        "phone",
        "created_at",
    )
    list_filter = ("session", "verification_status", "verification_method")
    search_fields = ("matric_number", "user__email", "user__first_name", "user__last_name")
    readonly_fields = ("created_at", "verified_at", "reviewed_at", "verification_notes")


@admin.register(LecturerProfile)
class LecturerProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "staff_number", "designation", "is_active")
    list_filter = ("is_active", "designation")
    search_fields = ("user__email", "user__first_name", "user__last_name", "staff_number")
    readonly_fields = ("created_at", "updated_at")


@admin.register(SupervisorAssignment)
class SupervisorAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        "student_enrollment",
        "lecturer",
        "is_current",
        "assigned_at",
        "ended_at",
    )
    list_filter = ("is_current", "student_enrollment__session")
    search_fields = (
        "student_enrollment__matric_number",
        "lecturer__user__email",
        "lecturer__user__first_name",
        "lecturer__user__last_name",
    )
    readonly_fields = ("assigned_at", "ended_at")
