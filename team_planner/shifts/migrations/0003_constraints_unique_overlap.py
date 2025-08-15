from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("shifts", "0002_alter_schedulingrule_shift_type_and_more"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="shift",
            constraint=models.UniqueConstraint(
                fields=["assigned_employee", "start_datetime", "end_datetime", "template"],
                name="unique_shift_per_employee_time_and_template",
            ),
        ),
        # Note: Overlap exclusion constraints require Postgres and btree_gist extension.
        # We'll add the extension and exclusion constraint in a separate migration
        # guarded for Postgres only in production settings.
    ]
