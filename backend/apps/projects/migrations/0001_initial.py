import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.utils import timezone


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("accounts", "0002_seed_system_roles"),
        ("academics", "0003_student_registration_verification_details"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ProjectTopic",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("title", models.CharField(max_length=300)),
                ("abstract", models.TextField()),
                ("problem_statement", models.TextField()),
                ("research_objectives", models.TextField()),
                ("keywords", models.JSONField(default=list)),
                ("status", models.CharField(choices=[("submitted", "Submitted"), ("revision_requested", "Revision requested"), ("approved", "Approved"), ("rejected", "Rejected")], default="submitted", max_length=24)),
                ("is_current", models.BooleanField(default=True)),
                ("submitted_at", models.DateTimeField(default=timezone.now)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("student_enrollment", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="project_topics", to="academics.studentenrollment")),
                ("supervisor_assignment", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="project_topics", to="academics.supervisorassignment")),
            ],
            options={
                "db_table": "projects_project_topic",
                "ordering": ["-submitted_at", "title"],
            },
        ),
        migrations.CreateModel(
            name="ProjectTopicRevision",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("revision_number", models.PositiveIntegerField()),
                ("title", models.CharField(max_length=300)),
                ("abstract", models.TextField()),
                ("problem_statement", models.TextField()),
                ("research_objectives", models.TextField()),
                ("keywords", models.JSONField(default=list)),
                ("submitted_at", models.DateTimeField(default=timezone.now)),
                ("submitted_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="project_topic_revisions", to=settings.AUTH_USER_MODEL)),
                ("topic", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="revisions", to="projects.projecttopic")),
            ],
            options={
                "db_table": "projects_project_topic_revision",
                "ordering": ["revision_number"],
            },
        ),
        migrations.CreateModel(
            name="ProjectTopicReview",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("decision", models.CharField(choices=[("approve", "Approve"), ("request_revision", "Request revision"), ("reject", "Reject")], max_length=24)),
                ("feedback", models.TextField(blank=True)),
                ("reviewed_at", models.DateTimeField(default=timezone.now)),
                ("reviewer", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="project_topic_reviews", to=settings.AUTH_USER_MODEL)),
                ("revision", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="reviews", to="projects.projecttopicrevision")),
                ("supervisor_assignment", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="project_topic_reviews", to="academics.supervisorassignment")),
                ("topic", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reviews", to="projects.projecttopic")),
            ],
            options={
                "db_table": "projects_project_topic_review",
                "ordering": ["-reviewed_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="projecttopic",
            constraint=models.UniqueConstraint(condition=models.Q(("is_current", True)), fields=("student_enrollment",), name="projects_one_current_topic_per_student"),
        ),
        migrations.AddIndex(
            model_name="projecttopic",
            index=models.Index(fields=["status", "submitted_at"], name="projects_topic_status_idx"),
        ),
        migrations.AddIndex(
            model_name="projecttopic",
            index=models.Index(fields=["supervisor_assignment", "status"], name="projects_topic_supervisor_idx"),
        ),
        migrations.AddConstraint(
            model_name="projecttopicrevision",
            constraint=models.UniqueConstraint(fields=("topic", "revision_number"), name="projects_unique_topic_revision"),
        ),
        migrations.AddIndex(
            model_name="projecttopicreview",
            index=models.Index(fields=["topic", "reviewed_at"], name="projects_topic_review_idx"),
        ),
    ]
