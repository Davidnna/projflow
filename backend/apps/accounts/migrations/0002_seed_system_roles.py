from django.db import migrations

ROLES = [
    ("administrator", "Administrator", "System administration and configuration."),
    ("project_coordinator", "Project Coordinator", "Departmental final-year project coordination."),
    ("lecturer", "Lecturer", "Lecturer account and academic responsibilities."),
    ("student", "Student", "Student account and project participation."),
]


def seed_roles(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    database = schema_editor.connection.alias
    for code, name, description in ROLES:
        Role.objects.using(database).get_or_create(
            code=code,
            defaults={"name": name, "description": description, "is_system": True},
        )


class Migration(migrations.Migration):
    dependencies = [("accounts", "0001_initial")]
    operations = [migrations.RunPython(seed_roles, migrations.RunPython.noop)]
