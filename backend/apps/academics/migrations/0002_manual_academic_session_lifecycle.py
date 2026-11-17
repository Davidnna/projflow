from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("academics", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="academicsession",
            name="start_date",
            field=models.DateField(blank=True, editable=False, null=True),
        ),
        migrations.AlterField(
            model_name="academicsession",
            name="end_date",
            field=models.DateField(blank=True, editable=False, null=True),
        ),
        migrations.AlterModelOptions(
            name="academicsession",
            options={"ordering": ["-created_at", "name"]},
        ),
    ]
