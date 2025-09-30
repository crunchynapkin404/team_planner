from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('shifts', '0003_constraints_unique_overlap'),
    ]

    operations = [
        # Skipping exclusion constraint for now due to column name issues
        # TODO: Fix this constraint after resolving field name conflicts
    ]
