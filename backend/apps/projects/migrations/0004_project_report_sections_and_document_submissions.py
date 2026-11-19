import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.utils import timezone


class Migration(migrations.Migration):
    dependencies = [
        ("academics", "0003_student_registration_verification_details"),
        ("projects", "0003_project_milestones_and_progress"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ProjectReportSection",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("title", models.CharField(max_length=200)),
                ("description", models.TextField(blank=True)),
                ("sequence", models.PositiveIntegerField()),
                ("due_date", models.DateField(blank=True, null=True)),
                ("is_required", models.BooleanField(default=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="project_report_sections_created", to=settings.AUTH_USER_MODEL)),
                ("session", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="project_report_sections", to="academics.academicsession")),
                ("updated_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="project_report_sections_updated", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "projects_report_section",
                "ordering": ["session__created_at", "sequence", "title"],
            },
        ),
        migrations.AddConstraint(
            model_name="projectreportsection",
            constraint=models.UniqueConstraint(fields=("session", "sequence"), name="projects_unique_report_section_order"),
        ),
        migrations.AddIndex(
            model_name="projectreportsection",
            index=models.Index(fields=["session", "is_active", "sequence"], name="projects_report_section_idx"),
        ),
        migrations.CreateModel(
            name="ProjectReportSubmission",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("status", models.CharField(choices=[("submitted", "Submitted"), ("revision_requested", "Revision requested"), ("approved", "Approved")], default="submitted", max_length=24)),
                ("submitted_at", models.DateTimeField(default=timezone.now)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("section", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="submissions", to="projects.projectreportsection")),
                ("student_enrollment", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="project_report_submissions", to="academics.studentenrollment")),
                ("supervisor_assignment", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="project_report_submissions", to="academics.supervisorassignment")),
            ],
            options={
                "db_table": "projects_report_submission",
                "ordering": ["-submitted_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="projectreportsubmission",
            constraint=models.UniqueConstraint(fields=("section", "student_enrollment"), name="projects_unique_student_report_section"),
        ),
        migrations.AddIndex(
            model_name="projectreportsubmission",
            index=models.Index(fields=["student_enrollment", "status"], name="projects_report_student_idx"),
        ),
        migrations.AddIndex(
            model_name="projectreportsubmission",
            index=models.Index(fields=["supervisor_assignment", "status"], name="projects_report_supervisor_idx"),
        ),
        migrations.CreateModel(
            name="ProjectReportRevision",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("revision_number", models.PositiveIntegerField()),
                ("storage_path", models.CharField(editable=False, max_length=512)),
                ("original_filename", models.CharField(max_length=255)),
                ("file_size", models.PositiveBigIntegerField()),
                ("content_type", models.CharField(max_length=120)),
                ("submission_note", models.TextField(blank=True)),
                ("submitted_at", models.DateTimeField(default=timezone.now)),
                ("submission", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="revisions", to="projects.projectreportsubmission")),
                ("uploaded_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="project_report_revisions_uploaded", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "projects_report_revision",
                "ordering": ["revision_number"],
            },
        ),
        migrations.AddConstraint(
            model_name="projectreportrevision",
            constraint=models.UniqueConstraint(fields=("submission", "revision_number"), name="projects_unique_report_revision"),
        ),
        migrations.CreateModel(
            name="ProjectReportReview",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("decision", models.CharField(choices=[("approve", "Approve"), ("request_revision", "Request revision")], max_length=24)),
                ("feedback", models.TextField(blank=True)),
                ("reviewed_at", models.DateTimeField(default=timezone.now)),
                ("revision", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="reviews", to="projects.projectreportrevision")),
                ("reviewer", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="project_report_reviews", to=settings.AUTH_USER_MODEL)),
                ("submission", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reviews", to="projects.projectreportsubmission")),
                ("supervisor_assignment", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="project_report_reviews", to="academics.supervisorassignment")),
            ],
            options={
                "db_table": "projects_report_review",
                "ordering": ["-reviewed_at"],
            },
        ),
        migrations.AddIndex(
            model_name="projectreportreview",
            index=models.Index(fields=["submission", "reviewed_at"], name="projects_report_review_idx"),
        ),
    ]
