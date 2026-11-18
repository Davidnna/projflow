import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("projects", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="projecttopicrevision",
            name="similarity_embeddings",
            field=models.JSONField(blank=True, default=dict, editable=False),
        ),
        migrations.AddField(
            model_name="projecttopicrevision",
            name="similarity_model_name",
            field=models.CharField(blank=True, editable=False, max_length=120),
        ),
        migrations.AddField(
            model_name="projecttopicrevision",
            name="similarity_status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("completed", "Completed"),
                    ("unavailable", "Unavailable"),
                ],
                default="pending",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="projecttopicrevision",
            name="similarity_analyzed_at",
            field=models.DateTimeField(blank=True, editable=False, null=True),
        ),
        migrations.CreateModel(
            name="ProjectTopicSimilarity",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("overall_score", models.FloatField()),
                ("field_scores", models.JSONField(default=dict)),
                ("threshold", models.FloatField()),
                ("model_name", models.CharField(max_length=120)),
                ("algorithm_version", models.CharField(max_length=32)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "matched_revision",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="similarity_sources",
                        to="projects.projecttopicrevision",
                    ),
                ),
                (
                    "source_revision",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="similarity_matches",
                        to="projects.projecttopicrevision",
                    ),
                ),
            ],
            options={
                "db_table": "projects_project_topic_similarity",
                "ordering": ["-overall_score", "matched_revision__title"],
            },
        ),
        migrations.AddConstraint(
            model_name="projecttopicsimilarity",
            constraint=models.UniqueConstraint(
                fields=("source_revision", "matched_revision"),
                name="projects_unique_topic_similarity_match",
            ),
        ),
        migrations.AddIndex(
            model_name="projecttopicsimilarity",
            index=models.Index(
                fields=["source_revision", "-overall_score"],
                name="projects_similarity_src_idx",
            ),
        ),
    ]
