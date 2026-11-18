import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.utils import timezone


class Migration(migrations.Migration):
    dependencies = [
        ("academics", "0003_student_registration_verification_details"),
        ("projects", "0002_topic_similarity_detection"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ProjectMilestone",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("title", models.CharField(max_length=200)),
                ("description", models.TextField(blank=True)),
                ("expected_achievement", models.TextField(blank=True)),
                ("sequence", models.PositiveIntegerField()),
                ("due_date", models.DateField(blank=True, null=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="project_milestones_created", to=settings.AUTH_USER_MODEL)),
                ("session", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="project_milestones", to="academics.academicsession")),
                ("updated_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="project_milestones_updated", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "projects_project_milestone",
                "ordering": ["session__created_at", "sequence", "title"],
            },
        ),
        migrations.AddConstraint(
            model_name="projectmilestone",
            constraint=models.UniqueConstraint(fields=("session", "sequence"), name="projects_unique_session_milestone_order"),
        ),
        migrations.AddIndex(
            model_name="projectmilestone",
            index=models.Index(fields=["session", "is_active", "sequence"], name="projects_milestone_session_idx"),
        ),
        migrations.CreateModel(
            name="ProjectProgressReport",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("status", models.CharField(choices=[("submitted", "Submitted"), ("revision_requested", "Revision requested"), ("reviewed", "Reviewed")], default="submitted", max_length=24)),
                ("submitted_at", models.DateTimeField(default=timezone.now)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("milestone", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="progress_reports", to="projects.projectmilestone")),
                ("student_enrollment", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="progress_reports", to="academics.studentenrollment")),
                ("supervisor_assignment", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="progress_reports", to="academics.supervisorassignment")),
            ],
            options={
                "db_table": "projects_progress_report",
                "ordering": ["-submitted_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="projectprogressreport",
            constraint=models.UniqueConstraint(fields=("milestone", "student_enrollment"), name="projects_unique_student_milestone_report"),
        ),
        migrations.AddIndex(
            model_name="projectprogressreport",
            index=models.Index(fields=["student_enrollment", "status"], name="projects_progress_student_idx"),
        ),
        migrations.AddIndex(
            model_name="projectprogressreport",
            index=models.Index(fields=["supervisor_assignment", "status"], name="projects_prog_supervisor_idx"),
        ),
        migrations.CreateModel(
            name="ProjectProgressRevision",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("revision_number", models.PositiveIntegerField()),
                ("completed_activities", models.TextField()),
                ("challenges", models.TextField(blank=True)),
                ("next_steps", models.TextField(blank=True)),
                ("submitted_at", models.DateTimeField(default=timezone.now)),
                ("report", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="revisions", to="projects.projectprogressreport")),
                ("submitted_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="project_progress_revisions", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "projects_progress_revision",
                "ordering": ["revision_number"],
            },
        ),
        migrations.AddConstraint(
            model_name="projectprogressrevision",
            constraint=models.UniqueConstraint(fields=("report", "revision_number"), name="projects_unique_progress_revision"),
        ),
        migrations.CreateModel(
            name="ProjectProgressReview",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("decision", models.CharField(choices=[("review", "Reviewed"), ("request_revision", "Request revision")], max_length=24)),
                ("assessment", models.CharField(choices=[("on_track", "On track"), ("needs_attention", "Needs attention"), ("behind_schedule", "Behind schedule"), ("completed", "Milestone completed")], max_length=24)),
                ("feedback", models.TextField(blank=True)),
                ("reviewed_at", models.DateTimeField(default=timezone.now)),
                ("report", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reviews", to="projects.projectprogressreport")),
                ("revision", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="reviews", to="projects.projectprogressrevision")),
                ("reviewer", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="project_progress_reviews", to=settings.AUTH_USER_MODEL)),
                ("supervisor_assignment", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="project_progress_reviews", to="academics.supervisorassignment")),
            ],
            options={
                "db_table": "projects_progress_review",
                "ordering": ["-reviewed_at"],
            },
        ),
        migrations.AddIndex(
            model_name="projectprogressreview",
            index=models.Index(fields=["report", "reviewed_at"], name="projects_progress_review_idx"),
        ),
    ]
