from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ("teams", "0002_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="team",
            name="timezone",
            field=models.CharField(
                default="Europe/Amsterdam",
                help_text="IANA timezone name for this team's scheduling (e.g., Europe/Amsterdam)",
                max_length=64,
                verbose_name="Timezone",
            ),
        ),
        migrations.AddField(
            model_name="team",
            name="waakdienst_handover_weekday",
            field=models.PositiveSmallIntegerField(
                default=2,
                help_text="0=Mon … 6=Sun; default Wednesday",
                validators=[
                    django.core.validators.MinValueValidator(0),
                    django.core.validators.MaxValueValidator(6),
                ],
                verbose_name="Waakdienst Handover Weekday",
            ),
        ),
        migrations.AddField(
            model_name="team",
            name="waakdienst_start_hour",
            field=models.PositiveSmallIntegerField(
                default=17,
                help_text="Hour of day (0–23) for waakdienst handover start; default 17",
                validators=[
                    django.core.validators.MinValueValidator(0),
                    django.core.validators.MaxValueValidator(23),
                ],
                verbose_name="Waakdienst Start Hour",
            ),
        ),
        migrations.AddField(
            model_name="team",
            name="waakdienst_end_hour",
            field=models.PositiveSmallIntegerField(
                default=8,
                help_text="Hour of day (0–23) for next handover end; default 8",
                validators=[
                    django.core.validators.MinValueValidator(0),
                    django.core.validators.MaxValueValidator(23),
                ],
                verbose_name="Waakdienst End Hour",
            ),
        ),
        migrations.AddField(
            model_name="team",
            name="incidents_skip_holidays",
            field=models.BooleanField(
                default=True,
                help_text="If true, do not generate incidents/standby on holidays; waakdienst continues",
                verbose_name="Skip Incidents/Standby on Holidays",
            ),
        ),
        migrations.AddField(
            model_name="team",
            name="standby_mode",
            field=models.CharField(
                choices=[
                    ("global_per_week", "Global per week"),
                    ("optional_per_week", "Optional per week"),
                ],
                default="optional_per_week",
                help_text="Initial policy for incidents-standby scheduling",
                max_length=32,
                verbose_name="Standby Mode",
            ),
        ),
        migrations.AddField(
            model_name="team",
            name="fairness_window_weeks",
            field=models.PositiveSmallIntegerField(
                default=26,
                help_text="Rolling window size for fairness calculations; default 26 weeks",
                validators=[
                    django.core.validators.MinValueValidator(1),
                    django.core.validators.MaxValueValidator(104),
                ],
                verbose_name="Fairness Window (weeks)",
            ),
        ),
        migrations.AddField(
            model_name="team",
            name="joiner_grace_weeks",
            field=models.PositiveSmallIntegerField(
                default=0,
                help_text="Weeks after joining before heavy shifts (e.g., waakdienst) are assigned",
                validators=[
                    django.core.validators.MinValueValidator(0),
                    django.core.validators.MaxValueValidator(52),
                ],
                verbose_name="Joiner Grace (weeks)",
            ),
        ),
        migrations.AddField(
            model_name="team",
            name="joiner_bootstrap_credit_hours",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                default=None,
                help_text="Optional initial credit hours for fairness; leave blank to disable",
                max_digits=5,
                null=True,
                verbose_name="Joiner Bootstrap Credit (hours)",
            ),
        ),
        migrations.AddField(
            model_name="teammembership",
            name="fte",
            field=models.DecimalField(
                decimal_places=2,
                default=1.0,
                help_text="Full-time equivalent (0.10 – 1.00); used for fairness weighting",
                max_digits=4,
                validators=[
                    django.core.validators.MinValueValidator(0.1),
                    django.core.validators.MaxValueValidator(1.0),
                ],
                verbose_name="FTE",
            ),
        ),
    ]
