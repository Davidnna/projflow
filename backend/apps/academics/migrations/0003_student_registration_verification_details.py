import re

from django.db import migrations, models


def normalise_name(value):
    return " ".join(str(value or "").strip().casefold().split())


def normalise_phone(value):
    return re.sub(r"[\s().-]", "", str(value or "")).casefold()


def populate_pending_verification_notes(apps, schema_editor):
    StudentEnrollment = apps.get_model("academics", "StudentEnrollment")
    StudentRosterRecord = apps.get_model("academics", "StudentRosterRecord")
    database = schema_editor.connection.alias

    pending_enrollments = StudentEnrollment.objects.using(database).filter(
        verification_status="pending_review"
    ).select_related("user", "roster_record")

    for enrollment in pending_enrollments.iterator():
        roster_record = enrollment.roster_record
        if roster_record is None:
            roster_record = StudentRosterRecord.objects.using(database).filter(
                session_id=enrollment.session_id,
                matric_number=enrollment.matric_number,
            ).first()

        if roster_record is None:
            notes = [
                "No matching matriculation number was found in the active session's departmental register."
            ]
        else:
            notes = []
            if not roster_record.is_eligible:
                notes.append(
                    "The departmental record is not marked as eligible for final-year project registration."
                )
            if normalise_name(roster_record.first_name) != normalise_name(enrollment.user.first_name):
                notes.append("First name does not match the departmental record.")
            if normalise_name(roster_record.last_name) != normalise_name(enrollment.user.last_name):
                notes.append("Last name does not match the departmental record.")
            if roster_record.other_names and normalise_name(roster_record.other_names) != normalise_name(enrollment.other_names):
                notes.append("Other names do not match the departmental record.")
            if roster_record.email and roster_record.email.strip().casefold() != enrollment.user.email.strip().casefold():
                notes.append("Email address does not match the departmental record.")
            if roster_record.phone and normalise_phone(roster_record.phone) != normalise_phone(enrollment.phone):
                notes.append("Phone number does not match the departmental record.")

        if notes:
            enrollment.verification_notes = " ".join(notes)
            enrollment.save(update_fields=["verification_notes"])



class Migration(migrations.Migration):
    dependencies = [
        ("academics", "0002_manual_academic_session_lifecycle"),
    ]

    operations = [
        migrations.AddField(
            model_name="studentenrollment",
            name="phone",
            field=models.CharField(blank=True, max_length=30),
        ),
        migrations.AddField(
            model_name="studentenrollment",
            name="verification_notes",
            field=models.TextField(blank=True),
        ),
        migrations.RunPython(
            populate_pending_verification_notes,
            migrations.RunPython.noop,
        ),
    ]
