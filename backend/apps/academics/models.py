import re
import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


class AcademicSessionStatus(models.TextChoices):
    PLANNED = "planned", "Planned"
    ACTIVE = "active", "Active"
    CLOSED = "closed", "Closed"


class StudentVerificationStatus(models.TextChoices):
    AUTO_VERIFIED = "auto_verified", "Automatically verified"
    PENDING_REVIEW = "pending_review", "Pending manual review"
    MANUALLY_APPROVED = "manually_approved", "Manually approved"
    REJECTED = "rejected", "Rejected"


class VerificationMethod(models.TextChoices):
    AUTOMATIC = "automatic", "Automatic"
    MANUAL = "manual", "Manual"


class RosterRecordSource(models.TextChoices):
    MANUAL = "manual", "Manual entry"
    IMPORT = "import", "Spreadsheet import"


class RosterImportStatus(models.TextChoices):
    PREVIEWED = "previewed", "Previewed"
    COMMITTED = "committed", "Committed"


class RosterImportRowStatus(models.TextChoices):
    VALID = "valid", "Valid"
    INVALID = "invalid", "Invalid"
    DUPLICATE = "duplicate", "Duplicate"


def normalise_matric_number(value):
    return re.sub(r"\s+", "", str(value or "")).upper()


def normalise_person_name(value):
    return " ".join(str(value or "").strip().casefold().split())


class AcademicSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    start_date = models.DateField(blank=True, null=True, editable=False)
    end_date = models.DateField(blank=True, null=True, editable=False)
    status = models.CharField(
        max_length=12,
        choices=AcademicSessionStatus.choices,
        default=AcademicSessionStatus.PLANNED,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="academic_sessions_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="academic_sessions_updated",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "academics_session"
        ordering = ["-created_at", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["status"],
                condition=Q(status=AcademicSessionStatus.ACTIVE),
                name="academics_one_active_session",
            )
        ]

    def __str__(self):
        return self.name


class StudentRosterRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        AcademicSession,
        on_delete=models.PROTECT,
        related_name="student_roster_records",
    )
    matric_number = models.CharField(max_length=40)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    other_names = models.CharField(max_length=150, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    is_eligible = models.BooleanField(default=True)
    source = models.CharField(
        max_length=10,
        choices=RosterRecordSource.choices,
        default=RosterRecordSource.MANUAL,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="student_roster_records_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="student_roster_records_updated",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "academics_student_roster_record"
        ordering = ["last_name", "first_name", "matric_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["session", "matric_number"],
                name="academics_unique_session_matric",
            )
        ]
        indexes = [
            models.Index(fields=["session", "last_name", "first_name"], name="acad_roster_session_name_idx"),
        ]

    def save(self, *args, **kwargs):
        self.matric_number = normalise_matric_number(self.matric_number)
        self.first_name = self.first_name.strip()
        self.last_name = self.last_name.strip()
        self.other_names = self.other_names.strip()
        self.email = self.email.strip().lower()
        self.phone = self.phone.strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.matric_number} - {self.last_name}, {self.first_name}"


class RosterImportBatch(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        AcademicSession,
        on_delete=models.PROTECT,
        related_name="roster_import_batches",
    )
    original_file_name = models.CharField(max_length=255)
    status = models.CharField(
        max_length=12,
        choices=RosterImportStatus.choices,
        default=RosterImportStatus.PREVIEWED,
    )
    total_rows = models.PositiveIntegerField(default=0)
    valid_rows = models.PositiveIntegerField(default=0)
    invalid_rows = models.PositiveIntegerField(default=0)
    duplicate_rows = models.PositiveIntegerField(default=0)
    imported_rows = models.PositiveIntegerField(default=0)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="roster_import_batches",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    committed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "academics_roster_import_batch"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.original_file_name} ({self.session.name})"


class RosterImportRow(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey(
        RosterImportBatch,
        on_delete=models.CASCADE,
        related_name="rows",
    )
    row_number = models.PositiveIntegerField()
    raw_data = models.JSONField(default=dict, blank=True)
    matric_number = models.CharField(max_length=40, blank=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    other_names = models.CharField(max_length=150, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    is_eligible = models.BooleanField(default=True)
    status = models.CharField(
        max_length=10,
        choices=RosterImportRowStatus.choices,
        default=RosterImportRowStatus.VALID,
    )
    errors = models.JSONField(default=list, blank=True)
    created_record = models.ForeignKey(
        StudentRosterRecord,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="import_rows",
    )

    class Meta:
        db_table = "academics_roster_import_row"
        ordering = ["row_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["batch", "row_number"],
                name="academics_unique_roster_import_row",
            )
        ]

    def __str__(self):
        return f"{self.batch_id} row {self.row_number}"


class StudentEnrollment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="student_enrollments",
    )
    session = models.ForeignKey(
        AcademicSession,
        on_delete=models.PROTECT,
        related_name="student_enrollments",
    )
    roster_record = models.ForeignKey(
        StudentRosterRecord,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="enrollments",
    )
    matric_number = models.CharField(max_length=40)
    other_names = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    verification_notes = models.TextField(blank=True)
    verification_status = models.CharField(
        max_length=20,
        choices=StudentVerificationStatus.choices,
        default=StudentVerificationStatus.PENDING_REVIEW,
    )
    verification_method = models.CharField(
        max_length=10,
        choices=VerificationMethod.choices,
        blank=True,
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="student_enrollments_reviewed",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "academics_student_enrollment"
        ordering = ["session__name", "matric_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["session", "user"],
                name="academics_unique_session_student",
            ),
            models.UniqueConstraint(
                fields=["session", "matric_number"],
                name="academics_unique_session_enrollment_matric",
            ),
            models.UniqueConstraint(
                fields=["roster_record"],
                condition=Q(roster_record__isnull=False),
                name="academics_unique_roster_enrollment",
            ),
        ]

    def clean(self):
        if self.roster_record_id and self.session_id:
            if self.roster_record.session_id != self.session_id:
                from django.core.exceptions import ValidationError

                raise ValidationError({"roster_record": "The roster record must belong to the same academic session."})

    def save(self, *args, **kwargs):
        self.matric_number = normalise_matric_number(self.matric_number)
        super().save(*args, **kwargs)

    @property
    def is_verified(self):
        return self.verification_status in {
            StudentVerificationStatus.AUTO_VERIFIED,
            StudentVerificationStatus.MANUALLY_APPROVED,
        }

    def __str__(self):
        return f"{self.matric_number} ({self.session.name})"


class LecturerProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="lecturer_profile",
    )
    staff_number = models.CharField(max_length=40, unique=True, null=True, blank=True)
    designation = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    office = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lecturer_profiles_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "academics_lecturer_profile"
        ordering = ["user__last_name", "user__first_name"]

    def save(self, *args, **kwargs):
        if self.staff_number is not None:
            self.staff_number = self.staff_number.strip().upper() or None
        self.designation = self.designation.strip()
        self.phone = self.phone.strip()
        self.office = self.office.strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.user.get_full_name() or self.user.email


class SupervisorAssignment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student_enrollment = models.ForeignKey(
        StudentEnrollment,
        on_delete=models.PROTECT,
        related_name="supervisor_assignments",
    )
    lecturer = models.ForeignKey(
        LecturerProfile,
        on_delete=models.PROTECT,
        related_name="supervisor_assignments",
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="supervisor_assignments_created",
    )
    assigned_at = models.DateTimeField(default=timezone.now)
    is_current = models.BooleanField(default=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    ended_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="supervisor_assignments_ended",
    )
    reassignment_reason = models.TextField(blank=True)

    class Meta:
        db_table = "academics_supervisor_assignment"
        ordering = ["-assigned_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["student_enrollment"],
                condition=Q(is_current=True),
                name="academics_one_current_supervisor",
            )
        ]
        indexes = [
            models.Index(fields=["lecturer", "is_current"], name="acad_supervisor_lecturer_idx"),
            models.Index(fields=["student_enrollment", "is_current"], name="acad_supervisor_student_idx"),
        ]

    def __str__(self):
        return f"{self.student_enrollment} -> {self.lecturer}"
