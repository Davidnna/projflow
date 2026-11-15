import uuid

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("accounts", "0002_seed_system_roles"),
    ]

    operations = [
        migrations.CreateModel(
            name="AcademicSession",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=100, unique=True)),
                ("start_date", models.DateField()),
                ("end_date", models.DateField()),
                (
                    "status",
                    models.CharField(
                        choices=[("planned", "Planned"), ("active", "Active"), ("closed", "Closed")],
                        default="planned",
                        max_length=12,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="academic_sessions_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="academic_sessions_updated",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "academics_session",
                "ordering": ["-start_date", "name"],
            },
        ),
        migrations.CreateModel(
            name="LecturerProfile",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("staff_number", models.CharField(blank=True, max_length=40, null=True, unique=True)),
                ("designation", models.CharField(blank=True, max_length=100)),
                ("phone", models.CharField(blank=True, max_length=30)),
                ("office", models.CharField(blank=True, max_length=100)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="lecturer_profiles_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="lecturer_profile",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "academics_lecturer_profile",
                "ordering": ["user__last_name", "user__first_name"],
            },
        ),
        migrations.CreateModel(
            name="RosterImportBatch",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("original_file_name", models.CharField(max_length=255)),
                (
                    "status",
                    models.CharField(
                        choices=[("previewed", "Previewed"), ("committed", "Committed")],
                        default="previewed",
                        max_length=12,
                    ),
                ),
                ("total_rows", models.PositiveIntegerField(default=0)),
                ("valid_rows", models.PositiveIntegerField(default=0)),
                ("invalid_rows", models.PositiveIntegerField(default=0)),
                ("duplicate_rows", models.PositiveIntegerField(default=0)),
                ("imported_rows", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("committed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "session",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="roster_import_batches",
                        to="academics.academicsession",
                    ),
                ),
                (
                    "uploaded_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="roster_import_batches",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "academics_roster_import_batch",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="StudentRosterRecord",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("matric_number", models.CharField(max_length=40)),
                ("first_name", models.CharField(max_length=150)),
                ("last_name", models.CharField(max_length=150)),
                ("other_names", models.CharField(blank=True, max_length=150)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("phone", models.CharField(blank=True, max_length=30)),
                ("is_eligible", models.BooleanField(default=True)),
                (
                    "source",
                    models.CharField(
                        choices=[("manual", "Manual entry"), ("import", "Spreadsheet import")],
                        default="manual",
                        max_length=10,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="student_roster_records_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "session",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="student_roster_records",
                        to="academics.academicsession",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="student_roster_records_updated",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "academics_student_roster_record",
                "ordering": ["last_name", "first_name", "matric_number"],
            },
        ),
        migrations.CreateModel(
            name="RosterImportRow",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("row_number", models.PositiveIntegerField()),
                ("raw_data", models.JSONField(blank=True, default=dict)),
                ("matric_number", models.CharField(blank=True, max_length=40)),
                ("first_name", models.CharField(blank=True, max_length=150)),
                ("last_name", models.CharField(blank=True, max_length=150)),
                ("other_names", models.CharField(blank=True, max_length=150)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("phone", models.CharField(blank=True, max_length=30)),
                ("is_eligible", models.BooleanField(default=True)),
                (
                    "status",
                    models.CharField(
                        choices=[("valid", "Valid"), ("invalid", "Invalid"), ("duplicate", "Duplicate")],
                        default="valid",
                        max_length=10,
                    ),
                ),
                ("errors", models.JSONField(blank=True, default=list)),
                (
                    "batch",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="rows",
                        to="academics.rosterimportbatch",
                    ),
                ),
                (
                    "created_record",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="import_rows",
                        to="academics.studentrosterrecord",
                    ),
                ),
            ],
            options={
                "db_table": "academics_roster_import_row",
                "ordering": ["row_number"],
            },
        ),
        migrations.CreateModel(
            name="StudentEnrollment",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("matric_number", models.CharField(max_length=40)),
                ("other_names", models.CharField(blank=True, max_length=150)),
                (
                    "verification_status",
                    models.CharField(
                        choices=[
                            ("auto_verified", "Automatically verified"),
                            ("pending_review", "Pending manual review"),
                            ("manually_approved", "Manually approved"),
                            ("rejected", "Rejected"),
                        ],
                        default="pending_review",
                        max_length=20,
                    ),
                ),
                (
                    "verification_method",
                    models.CharField(
                        blank=True,
                        choices=[("automatic", "Automatic"), ("manual", "Manual")],
                        max_length=10,
                    ),
                ),
                ("verified_at", models.DateTimeField(blank=True, null=True)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("review_notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "reviewed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="student_enrollments_reviewed",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "roster_record",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="enrollments",
                        to="academics.studentrosterrecord",
                    ),
                ),
                (
                    "session",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="student_enrollments",
                        to="academics.academicsession",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="student_enrollments",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "academics_student_enrollment",
                "ordering": ["session__name", "matric_number"],
            },
        ),
        migrations.CreateModel(
            name="SupervisorAssignment",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("assigned_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("is_current", models.BooleanField(default=True)),
                ("ended_at", models.DateTimeField(blank=True, null=True)),
                ("reassignment_reason", models.TextField(blank=True)),
                (
                    "assigned_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="supervisor_assignments_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "ended_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="supervisor_assignments_ended",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "lecturer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="supervisor_assignments",
                        to="academics.lecturerprofile",
                    ),
                ),
                (
                    "student_enrollment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="supervisor_assignments",
                        to="academics.studentenrollment",
                    ),
                ),
            ],
            options={
                "db_table": "academics_supervisor_assignment",
                "ordering": ["-assigned_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="academicsession",
            constraint=models.UniqueConstraint(
                condition=Q(status="active"),
                fields=("status",),
                name="academics_one_active_session",
            ),
        ),
        migrations.AddConstraint(
            model_name="studentrosterrecord",
            constraint=models.UniqueConstraint(
                fields=("session", "matric_number"),
                name="academics_unique_session_matric",
            ),
        ),
        migrations.AddIndex(
            model_name="studentrosterrecord",
            index=models.Index(fields=["session", "last_name", "first_name"], name="acad_roster_session_name_idx"),
        ),
        migrations.AddConstraint(
            model_name="rosterimportrow",
            constraint=models.UniqueConstraint(
                fields=("batch", "row_number"),
                name="academics_unique_roster_import_row",
            ),
        ),
        migrations.AddConstraint(
            model_name="studentenrollment",
            constraint=models.UniqueConstraint(
                fields=("session", "user"),
                name="academics_unique_session_student",
            ),
        ),
        migrations.AddConstraint(
            model_name="studentenrollment",
            constraint=models.UniqueConstraint(
                fields=("session", "matric_number"),
                name="academics_unique_session_enrollment_matric",
            ),
        ),
        migrations.AddConstraint(
            model_name="studentenrollment",
            constraint=models.UniqueConstraint(
                condition=Q(roster_record__isnull=False),
                fields=("roster_record",),
                name="academics_unique_roster_enrollment",
            ),
        ),
        migrations.AddIndex(
            model_name="supervisorassignment",
            index=models.Index(fields=["lecturer", "is_current"], name="acad_supervisor_lecturer_idx"),
        ),
        migrations.AddIndex(
            model_name="supervisorassignment",
            index=models.Index(fields=["student_enrollment", "is_current"], name="acad_supervisor_student_idx"),
        ),
        migrations.AddConstraint(
            model_name="supervisorassignment",
            constraint=models.UniqueConstraint(
                condition=Q(is_current=True),
                fields=("student_enrollment",),
                name="academics_one_current_supervisor",
            ),
        ),
    ]
