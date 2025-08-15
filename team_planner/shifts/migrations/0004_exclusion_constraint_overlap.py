from django.db import migrations


def add_exclusion_constraint(apps, schema_editor):
    # Only for PostgreSQL
    if schema_editor.connection.vendor != 'postgresql':
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("CREATE EXTENSION IF NOT EXISTS btree_gist;")
        # Prevent overlapping shifts per employee for active statuses
        cursor.execute(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint WHERE conname = 'shift_employee_no_overlap'
                ) THEN
                    ALTER TABLE shifts_shift
                    ADD CONSTRAINT shift_employee_no_overlap
                    EXCLUDE USING gist (
                        assigned_employee WITH =,
                        tstzrange(start_datetime, end_datetime) WITH &&
                    )
                    WHERE (status IN ('scheduled','in_progress','confirmed'));
                END IF;
            END$$;
            """
        )


def remove_exclusion_constraint(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM pg_constraint WHERE conname = 'shift_employee_no_overlap'
                ) THEN
                    ALTER TABLE shifts_shift DROP CONSTRAINT shift_employee_no_overlap;
                END IF;
            END$$;
            """
        )


class Migration(migrations.Migration):

    dependencies = [
        ('shifts', '0003_constraints_unique_overlap'),
    ]

    operations = [
        migrations.RunPython(add_exclusion_constraint, remove_exclusion_constraint),
    ]
