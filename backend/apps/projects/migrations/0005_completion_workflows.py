import uuid

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("projects", "0004_project_report_sections_and_document_submissions"),
        ("academics", "0003_student_registration_verification_details"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="projectreportreview",
            name="annotation_path",
            field=models.CharField(max_length=500, blank=True, default=""),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="projectreportreview",
            name="annotation_filename",
            field=models.CharField(max_length=255, blank=True, default=""),
            preserve_default=False,
        ),
        migrations.CreateModel(
            name="ProjectDeadline",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("session", models.ForeignKey('academics.academicsession', on_delete=models.PROTECT, related_name="project_deadlines")),
                ("kind", models.CharField(max_length=20)),
                ("due_date", models.DateField()),
                ("updated_by", models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="project_deadlines_updated")),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"constraints": [models.UniqueConstraint(fields=["session", "kind"], name="pf_deadline_session_kind")]},
        ),
        migrations.CreateModel(
            name="DeadlineExtension",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("enrollment", models.ForeignKey('academics.studentenrollment', on_delete=models.PROTECT, related_name="deadline_extensions")),
                ("kind", models.CharField(max_length=80)),
                ("original_due_date", models.DateField()),
                ("requested_date", models.DateField()),
                ("justification", models.TextField()),
                ("status", models.CharField(max_length=20, default="pending")),
                ("decision_note", models.TextField(blank=True)),
                ("decided_by", models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, related_name="extensions_decided")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("decided_at", models.DateTimeField(null=True)),
            ],
        ),
        migrations.CreateModel(
            name="AssessmentScheme",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("session", models.ForeignKey('academics.academicsession', on_delete=models.PROTECT, related_name="assessment_schemes")),
                ("lecturer", models.ForeignKey('academics.lecturerprofile', on_delete=models.PROTECT, related_name="assessment_schemes")),
                ("components", models.JSONField(default=list)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"constraints": [models.UniqueConstraint(fields=["session", "lecturer"], name="pf_scheme_session_lecturer")]},
        ),
        migrations.CreateModel(
            name="DefencePanel",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("session", models.ForeignKey('academics.academicsession', on_delete=models.PROTECT, related_name="defence_panels")),
                ("name", models.CharField(max_length=150)),
                ("members", models.ManyToManyField('academics.lecturerprofile', related_name="defence_panels")),
                ("created_by", models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="defence_panels_created")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"constraints": [models.UniqueConstraint(fields=["session", "name"], name="pf_panel_session_name")]},
        ),
        migrations.CreateModel(
            name="ProjectCompletion",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("enrollment", models.OneToOneField('academics.studentenrollment', on_delete=models.PROTECT, related_name="project_completion")),
                ("status", models.CharField(max_length=30, default="submitted")),
                ("panel", models.ForeignKey('projects.defencepanel', on_delete=models.PROTECT, null=True, related_name="projects")),
                ("defence_at", models.DateTimeField(null=True)),
                ("venue", models.CharField(max_length=200, blank=True)),
                ("components", models.JSONField(default=list)),
                ("score_round", models.PositiveIntegerField(default=1)),
                ("published_result", models.JSONField(default=dict)),
                ("published_at", models.DateTimeField(null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name="FinalReportVersion",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("project", models.ForeignKey('projects.projectcompletion', on_delete=models.PROTECT, related_name="documents")),
                ("version", models.PositiveIntegerField()),
                ("storage_path", models.CharField(max_length=500, unique=True)),
                ("original_filename", models.CharField(max_length=255)),
                ("file_size", models.PositiveIntegerField()),
                ("content_type", models.CharField(max_length=150)),
                ("note", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"constraints": [models.UniqueConstraint(fields=["project", "version"], name="pf_final_document_version")]},
        ),
        migrations.CreateModel(
            name="ExaminerScore",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("project", models.ForeignKey('projects.projectcompletion', on_delete=models.PROTECT, related_name="scores")),
                ("examiner", models.ForeignKey('academics.lecturerprofile', on_delete=models.PROTECT, related_name="examination_scores")),
                ("round", models.PositiveIntegerField()),
                ("marks", models.JSONField(default=list)),
                ("submitted_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"constraints": [models.UniqueConstraint(fields=["project", "examiner", "round"], name="pf_score_examiner_round")]},
        ),
        migrations.CreateModel(
            name="ResultAppeal",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("project", models.ForeignKey('projects.projectcompletion', on_delete=models.PROTECT, related_name="appeals")),
                ("complaint", models.TextField()),
                ("status", models.CharField(max_length=20, default="pending")),
                ("panel_feedback", models.TextField(blank=True)),
                ("panel_reviewer", models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, related_name="appeals_reviewed")),
                ("decision_note", models.TextField(blank=True)),
                ("decided_by", models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, related_name="appeals_decided")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("reviewed_at", models.DateTimeField(null=True)),
                ("decided_at", models.DateTimeField(null=True)),
            ],
        ),
        migrations.CreateModel(
            name="CompletionEvent",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("project", models.ForeignKey('projects.projectcompletion', on_delete=models.PROTECT, related_name="events")),
                ("actor", models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="completion_events")),
                ("action", models.CharField(max_length=40)),
                ("note", models.TextField(blank=True)),
                ("data", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name="ProjectNotification",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("recipient", models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="project_notifications")),
                ("category", models.CharField(max_length=30)),
                ("message", models.CharField(max_length=500)),
                ("read_at", models.DateTimeField(null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name="NotificationPreference",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("user", models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="project_notification_preferences")),
                ("categories", models.JSONField(default=dict)),
            ],
        ),
    ]
