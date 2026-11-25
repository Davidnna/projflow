from django.db import migrations
from django.utils import timezone


def clean_conflicting_accounts(apps, schema_editor):
    database = schema_editor.connection.alias
    Role = apps.get_model("accounts", "Role")
    UserRole = apps.get_model("accounts", "UserRole")
    LecturerProfile = apps.get_model("academics", "LecturerProfile")
    StudentEnrollment = apps.get_model("academics", "StudentEnrollment")
    SupervisorAssignment = apps.get_model("academics", "SupervisorAssignment")
    DefencePanel = apps.get_model("projects", "DefencePanel")
    ProjectCompletion = apps.get_model("projects", "ProjectCompletion")
    CompletionEvent = apps.get_model("projects", "CompletionEvent")
    ProjectNotification = apps.get_model("projects", "ProjectNotification")

    student_role = Role.objects.using(database).filter(code="student").first()
    lecturer_role = Role.objects.using(database).filter(code="lecturer").first()
    if student_role is None or lecturer_role is None:
        return

    conflicting_user_ids = set(
        UserRole.objects.using(database)
        .filter(role_id=student_role.pk)
        .values_list("user_id", flat=True)
    )
    enrolled_user_ids = set(
        StudentEnrollment.objects.using(database).values_list("user_id", flat=True)
    )
    conflicting_user_ids.update(enrolled_user_ids)
    if not conflicting_user_ids:
        return
    conflicting_user_ids = list(conflicting_user_ids)

    profile_ids = list(
        LecturerProfile.objects.using(database)
        .filter(user_id__in=conflicting_user_ids)
        .values_list("pk", flat=True)
    )
    if profile_ids:
        now = timezone.now()
        affected_enrollment_ids = set()
        assignments = SupervisorAssignment.objects.using(database).filter(
            lecturer_id__in=profile_ids,
            is_current=True,
        )
        for assignment in assignments.iterator():
            affected_enrollment_ids.add(assignment.student_enrollment_id)
            existing_reason = assignment.reassignment_reason.strip()
            closure_reason = (
                "Closed during the Student/Lecturer role-integrity migration; "
                "student accounts cannot hold Lecturer roles."
            )
            assignment.is_current = False
            assignment.ended_at = now
            assignment.reassignment_reason = (
                f"{existing_reason}\n{closure_reason}" if existing_reason else closure_reason
            )
            assignment.save(
                using=database,
                update_fields=["is_current", "ended_at", "reassignment_reason"],
            )

        LecturerProfile.objects.using(database).filter(pk__in=profile_ids).update(
            is_active=False,
            updated_at=now,
        )

        affected_projects = list(
            ProjectCompletion.objects.using(database)
            .filter(panel__members__pk__in=profile_ids)
            .select_related("panel", "enrollment")
            .distinct()
        )
        coordinator_ids = set(
            UserRole.objects.using(database)
            .filter(
                role__code__in=["project_coordinator", "administrator"],
                user__is_active=True,
            )
            .values_list("user_id", flat=True)
        )
        affected_student_user_ids = set(
            StudentEnrollment.objects.using(database)
            .filter(pk__in=affected_enrollment_ids)
            .values_list("user_id", flat=True)
        )
        supervision_student_message = (
            "Your supervisor assignment has been updated by the department. Contact your "
            "Project Coordinator if you need guidance. Your submitted academic records remain intact."
        )
        supervision_coordinator_message = (
            "A supervisor assignment requires attention. Assign an eligible Lecturer before "
            "the student proceeds. The previous assignment remains in the audit history."
        )
        for student_user_id in affected_student_user_ids:
            for recipient_id in coordinator_ids:
                ProjectNotification.objects.using(database).create(
                    recipient_id=recipient_id,
                    category="supervision",
                    message=supervision_coordinator_message,
                )
            ProjectNotification.objects.using(database).create(
                recipient_id=student_user_id,
                category="supervision",
                message=supervision_student_message,
            )

        for project in affected_projects:
            old_panel = project.panel
            invalid_member_ids = list(
                old_panel.members.using(database)
                .filter(pk__in=profile_ids)
                .values_list("pk", flat=True)
            )
            previous_published_at = (
                project.published_at.isoformat() if project.published_at else None
            )
            CompletionEvent.objects.using(database).create(
                project_id=project.pk,
                actor_id=old_panel.created_by_id,
                action="panel_reallocation_required",
                note=(
                    "The examination panel has been reset and must be reallocated before the "
                    "project can proceed. Previous score records and any earlier result have "
                    "been retained for audit."
                ),
                data={
                    "previous_panel_id": str(old_panel.pk),
                    "previous_panel_name": old_panel.name,
                    "invalid_examiner_profile_ids": [str(value) for value in invalid_member_ids],
                    "previous_status": project.status,
                    "previous_score_round": project.score_round,
                    "previous_score_count": project.scores.count(),
                    "previous_defence_at": project.defence_at.isoformat() if project.defence_at else None,
                    "previous_venue": project.venue,
                    "previous_components": project.components,
                    "previous_published_result": project.published_result,
                    "previous_published_at": previous_published_at,
                },
            )
            project.score_round += 1
            project.status = "panel_reallocation_required"
            project.panel = None
            project.defence_at = None
            project.venue = ""
            project.components = []
            project.published_result = {}
            project.published_at = None
            project.save(
                using=database,
                update_fields=[
                    "score_round",
                    "status",
                    "panel",
                    "defence_at",
                    "venue",
                    "components",
                    "published_result",
                    "published_at",
                    "updated_at",
                ],
            )

            coordinator_message = (
                "A defence panel requires reallocation before the affected project can "
                "proceed. Previous scores and any earlier result have been retained in the audit history."
            )
            for recipient_id in coordinator_ids:
                ProjectNotification.objects.using(database).create(
                    recipient_id=recipient_id,
                    category="defence",
                    message=coordinator_message,
                )
            ProjectNotification.objects.using(database).create(
                recipient_id=project.enrollment.user_id,
                category="defence",
                message=(
                    "Your defence arrangements need to be updated. The Project Coordinator "
                    "will provide a revised panel and schedule. Your submitted documents and "
                    "previous assessment records have been retained."
                ),
            )

        for panel in DefencePanel.objects.using(database).filter(
            members__pk__in=profile_ids
        ).distinct():
            panel.members.remove(*profile_ids)

    UserRole.objects.using(database).filter(
        user_id__in=conflicting_user_ids,
        role_id=lecturer_role.pk,
    ).delete()

    for user_id in enrolled_user_ids:
        UserRole.objects.using(database).get_or_create(
            user_id=user_id,
            role_id=student_role.pk,
        )


def install_role_triggers(apps, schema_editor):
    vendor = schema_editor.connection.vendor
    if vendor == "sqlite":
        schema_editor.execute(
            """
            CREATE TRIGGER accounts_role_exclusivity_insert
            BEFORE INSERT ON accounts_user_role
            FOR EACH ROW
            WHEN EXISTS (
                SELECT 1
                FROM accounts_user_role existing_assignment
                JOIN accounts_role existing_role
                    ON existing_role.id = existing_assignment.role_id
                JOIN accounts_role incoming_role
                    ON incoming_role.id = NEW.role_id
                WHERE existing_assignment.user_id = NEW.user_id
                AND (
                    (incoming_role.code = 'student' AND existing_role.code = 'lecturer')
                    OR
                    (incoming_role.code = 'lecturer' AND existing_role.code = 'student')
                )
            )
            OR (
                (SELECT code FROM accounts_role WHERE id = NEW.role_id) = 'lecturer'
                AND EXISTS (
                    SELECT 1 FROM academics_student_enrollment enrollment
                    WHERE enrollment.user_id = NEW.user_id
                )
            )
            OR (
                (SELECT code FROM accounts_role WHERE id = NEW.role_id) = 'student'
                AND EXISTS (
                    SELECT 1 FROM academics_lecturer_profile profile
                    WHERE profile.user_id = NEW.user_id AND profile.is_active = 1
                )
            )
            BEGIN
                SELECT RAISE(ABORT, 'A user cannot hold both Student and Lecturer roles.');
            END;
            """
        )
        schema_editor.execute(
            """
            CREATE TRIGGER accounts_role_exclusivity_update
            BEFORE UPDATE OF user_id, role_id ON accounts_user_role
            FOR EACH ROW
            WHEN EXISTS (
                SELECT 1
                FROM accounts_user_role existing_assignment
                JOIN accounts_role existing_role
                    ON existing_role.id = existing_assignment.role_id
                JOIN accounts_role incoming_role
                    ON incoming_role.id = NEW.role_id
                WHERE existing_assignment.user_id = NEW.user_id
                AND existing_assignment.id <> OLD.id
                AND (
                    (incoming_role.code = 'student' AND existing_role.code = 'lecturer')
                    OR
                    (incoming_role.code = 'lecturer' AND existing_role.code = 'student')
                )
            )
            OR (
                (SELECT code FROM accounts_role WHERE id = NEW.role_id) = 'lecturer'
                AND EXISTS (
                    SELECT 1 FROM academics_student_enrollment enrollment
                    WHERE enrollment.user_id = NEW.user_id
                )
            )
            OR (
                (SELECT code FROM accounts_role WHERE id = NEW.role_id) = 'student'
                AND EXISTS (
                    SELECT 1 FROM academics_lecturer_profile profile
                    WHERE profile.user_id = NEW.user_id AND profile.is_active = 1
                )
            )
            BEGIN
                SELECT RAISE(ABORT, 'A user cannot hold both Student and Lecturer roles.');
            END;
            """
        )
        schema_editor.execute(
            """
            CREATE TRIGGER academics_enrollment_reject_lecturers_insert
            BEFORE INSERT ON academics_student_enrollment
            FOR EACH ROW
            WHEN EXISTS (
                SELECT 1
                FROM accounts_user_role assignment
                JOIN accounts_role role ON role.id = assignment.role_id
                WHERE assignment.user_id = NEW.user_id
                AND role.code = 'lecturer'
            )
            OR EXISTS (
                SELECT 1 FROM academics_lecturer_profile profile
                WHERE profile.user_id = NEW.user_id AND profile.is_active = 1
            )
            BEGIN
                SELECT RAISE(ABORT, 'A Lecturer account cannot be enrolled as a student.');
            END;
            """
        )
        schema_editor.execute(
            """
            CREATE TRIGGER academics_enrollment_reject_lecturers_update
            BEFORE UPDATE OF user_id ON academics_student_enrollment
            FOR EACH ROW
            WHEN EXISTS (
                SELECT 1
                FROM accounts_user_role assignment
                JOIN accounts_role role ON role.id = assignment.role_id
                WHERE assignment.user_id = NEW.user_id
                AND role.code = 'lecturer'
            )
            OR EXISTS (
                SELECT 1 FROM academics_lecturer_profile profile
                WHERE profile.user_id = NEW.user_id AND profile.is_active = 1
            )
            BEGIN
                SELECT RAISE(ABORT, 'A Lecturer account cannot be enrolled as a student.');
            END;
            """
        )
        schema_editor.execute(
            """
            CREATE TRIGGER academics_profile_reject_students_insert
            BEFORE INSERT ON academics_lecturer_profile
            FOR EACH ROW
            WHEN NEW.is_active = 1 AND (
                EXISTS (
                    SELECT 1
                    FROM accounts_user_role assignment
                    JOIN accounts_role role ON role.id = assignment.role_id
                    WHERE assignment.user_id = NEW.user_id
                    AND role.code = 'student'
                ) OR EXISTS (
                    SELECT 1 FROM academics_student_enrollment enrollment
                    WHERE enrollment.user_id = NEW.user_id
                )
            )
            BEGIN
                SELECT RAISE(ABORT, 'A student account cannot have a Lecturer profile.');
            END;
            """
        )
        schema_editor.execute(
            """
            CREATE TRIGGER academics_profile_reject_students_update
            BEFORE UPDATE OF user_id, is_active ON academics_lecturer_profile
            FOR EACH ROW
            WHEN NEW.is_active = 1 AND (
                EXISTS (
                    SELECT 1
                    FROM accounts_user_role assignment
                    JOIN accounts_role role ON role.id = assignment.role_id
                    WHERE assignment.user_id = NEW.user_id
                    AND role.code = 'student'
                ) OR EXISTS (
                    SELECT 1 FROM academics_student_enrollment enrollment
                    WHERE enrollment.user_id = NEW.user_id
                )
            )
            BEGIN
                SELECT RAISE(ABORT, 'A student account cannot have a Lecturer profile.');
            END;
            """
        )
        return

    if vendor == "postgresql":
        schema_editor.execute(
            """
            CREATE OR REPLACE FUNCTION accounts_enforce_student_lecturer_exclusivity()
            RETURNS trigger AS $$
            DECLARE
                incoming_role_code text;
            BEGIN
                SELECT code INTO incoming_role_code
                FROM accounts_role
                WHERE id = NEW.role_id;

                IF incoming_role_code IN ('student', 'lecturer') AND EXISTS (
                    SELECT 1
                    FROM accounts_user_role existing_assignment
                    JOIN accounts_role existing_role
                        ON existing_role.id = existing_assignment.role_id
                    WHERE existing_assignment.user_id = NEW.user_id
                    AND existing_assignment.id IS DISTINCT FROM NEW.id
                    AND (
                        (incoming_role_code = 'student' AND existing_role.code = 'lecturer')
                        OR
                        (incoming_role_code = 'lecturer' AND existing_role.code = 'student')
                    )
                ) THEN
                    RAISE EXCEPTION USING
                        ERRCODE = '23514',
                        MESSAGE = 'A user cannot hold both Student and Lecturer roles.';
                END IF;

                IF incoming_role_code = 'lecturer' AND EXISTS (
                    SELECT 1
                    FROM academics_student_enrollment enrollment
                    WHERE enrollment.user_id = NEW.user_id
                ) THEN
                    RAISE EXCEPTION USING
                        ERRCODE = '23514',
                        MESSAGE = 'A student account cannot be assigned the Lecturer role.';
                END IF;

                IF incoming_role_code = 'student' AND EXISTS (
                    SELECT 1
                    FROM academics_lecturer_profile profile
                    WHERE profile.user_id = NEW.user_id AND profile.is_active
                ) THEN
                    RAISE EXCEPTION USING
                        ERRCODE = '23514',
                        MESSAGE = 'An active Lecturer profile cannot be assigned the Student role.';
                END IF;

                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        schema_editor.execute(
            """
            CREATE TRIGGER accounts_role_exclusivity
            BEFORE INSERT OR UPDATE OF user_id, role_id ON accounts_user_role
            FOR EACH ROW
            EXECUTE FUNCTION accounts_enforce_student_lecturer_exclusivity();
            """
        )
        schema_editor.execute(
            """
            CREATE OR REPLACE FUNCTION academics_reject_lecturer_student_enrollment()
            RETURNS trigger AS $$
            BEGIN
                IF EXISTS (
                    SELECT 1
                    FROM accounts_user_role assignment
                    JOIN accounts_role role ON role.id = assignment.role_id
                    WHERE assignment.user_id = NEW.user_id
                    AND role.code = 'lecturer'
                ) OR EXISTS (
                    SELECT 1
                    FROM academics_lecturer_profile profile
                    WHERE profile.user_id = NEW.user_id AND profile.is_active
                ) THEN
                    RAISE EXCEPTION USING
                        ERRCODE = '23514',
                        MESSAGE = 'A Lecturer account cannot be enrolled as a student.';
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        schema_editor.execute(
            """
            CREATE TRIGGER academics_enrollment_reject_lecturers
            BEFORE INSERT OR UPDATE OF user_id ON academics_student_enrollment
            FOR EACH ROW
            EXECUTE FUNCTION academics_reject_lecturer_student_enrollment();
            """
        )
        schema_editor.execute(
            """
            CREATE OR REPLACE FUNCTION academics_reject_student_lecturer_profile()
            RETURNS trigger AS $$
            BEGIN
                IF NEW.is_active AND (
                    EXISTS (
                        SELECT 1
                        FROM accounts_user_role assignment
                        JOIN accounts_role role ON role.id = assignment.role_id
                        WHERE assignment.user_id = NEW.user_id
                        AND role.code = 'student'
                    ) OR EXISTS (
                        SELECT 1
                        FROM academics_student_enrollment enrollment
                        WHERE enrollment.user_id = NEW.user_id
                    )
                ) THEN
                    RAISE EXCEPTION USING
                        ERRCODE = '23514',
                        MESSAGE = 'A student account cannot have a Lecturer profile.';
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        schema_editor.execute(
            """
            CREATE TRIGGER academics_profile_reject_students
            BEFORE INSERT OR UPDATE OF user_id, is_active ON academics_lecturer_profile
            FOR EACH ROW
            EXECUTE FUNCTION academics_reject_student_lecturer_profile();
            """
        )
        return

    raise RuntimeError(
        f"Student/Lecturer role protection is not configured for database vendor '{vendor}'."
    )


def remove_role_triggers(apps, schema_editor):
    vendor = schema_editor.connection.vendor
    if vendor == "sqlite":
        schema_editor.execute("DROP TRIGGER IF EXISTS accounts_role_exclusivity_insert")
        schema_editor.execute("DROP TRIGGER IF EXISTS accounts_role_exclusivity_update")
        schema_editor.execute("DROP TRIGGER IF EXISTS academics_enrollment_reject_lecturers_insert")
        schema_editor.execute("DROP TRIGGER IF EXISTS academics_enrollment_reject_lecturers_update")
        schema_editor.execute("DROP TRIGGER IF EXISTS academics_profile_reject_students_insert")
        schema_editor.execute("DROP TRIGGER IF EXISTS academics_profile_reject_students_update")
    elif vendor == "postgresql":
        schema_editor.execute("DROP TRIGGER IF EXISTS accounts_role_exclusivity ON accounts_user_role")
        schema_editor.execute("DROP FUNCTION IF EXISTS accounts_enforce_student_lecturer_exclusivity()")
        schema_editor.execute("DROP TRIGGER IF EXISTS academics_enrollment_reject_lecturers ON academics_student_enrollment")
        schema_editor.execute("DROP FUNCTION IF EXISTS academics_reject_lecturer_student_enrollment()")
        schema_editor.execute("DROP TRIGGER IF EXISTS academics_profile_reject_students ON academics_lecturer_profile")
        schema_editor.execute("DROP FUNCTION IF EXISTS academics_reject_student_lecturer_profile()")


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_seed_system_roles"),
        ("academics", "0003_student_registration_verification_details"),
        ("projects", "0005_completion_workflows"),
    ]

    operations = [
        migrations.RunPython(clean_conflicting_accounts, migrations.RunPython.noop),
        migrations.RunPython(install_role_triggers, remove_role_triggers),
    ]
