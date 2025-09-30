"""
Audit waakdienst eligibility for a given team.

Usage examples:
  /bin/python3 manage.py waakdienst_audit --team-id 7
  /bin/python3 manage.py waakdienst_audit --team-name "Team 7"
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError

from team_planner.employees.models import EmployeeProfile
from team_planner.teams.models import Team


class Command(BaseCommand):
    help = "Audit waakdienst eligibility (by flag and by skill) for a team"

    def add_arguments(self, parser):
        parser.add_argument("--team-id", type=int, help="Team ID")
        parser.add_argument(
            "--team-name", type=str, help="Team name (case-insensitive)",
        )

    def handle(self, *args, **options):
        team_id = options.get("team_id")
        team_name = options.get("team_name")

        if not team_id and not team_name:
            msg = "Provide --team-id or --team-name"
            raise CommandError(msg)

        team = None
        if team_id:
            try:
                team = Team.objects.get(pk=team_id)
            except Team.DoesNotExist:
                msg = f"Team with id={team_id} not found"
                raise CommandError(msg)
        else:
            team = (
                Team.objects.filter(name__iexact=team_name).first()
                or Team.objects.filter(name__icontains=team_name).first()
            )
            if not team:
                msg = f"Team with name like '{team_name}' not found"
                raise CommandError(msg)

        User = get_user_model()
        members = (
            User.objects.filter(teams=team, is_active=True)
            .select_related("employee_profile")
            .order_by("username")
        )
        profs = EmployeeProfile.objects.filter(user__in=members)

        eligible_flag = profs.filter(available_for_waakdienst=True)
        eligible_skill = profs.filter(
            skills__name="waakdienst", skills__is_active=True,
        ).distinct()

        # Union of user IDs
        flag_ids = set(eligible_flag.values_list("user_id", flat=True))
        skill_ids = set(eligible_skill.values_list("user_id", flat=True))
        union_ids = flag_ids | skill_ids

        # Build username lists
        usernames_flag = list(eligible_flag.values_list("user__username", flat=True))
        usernames_skill = list(eligible_skill.values_list("user__username", flat=True))
        usernames_union = list(
            members.filter(pk__in=union_ids).values_list("username", flat=True),
        )

        self.stdout.write(self.style.SUCCESS(f"Team: {team.pk} - {team}"))
        self.stdout.write(f"Members (active): {members.count()}")
        self.stdout.write(
            f"Eligible by flag (available_for_waakdienst=True): {len(flag_ids)}",
        )
        self.stdout.write(
            f"Eligible by skill (skill=waakdienst, active): {len(skill_ids)}",
        )
        self.stdout.write(
            self.style.SUCCESS(f"Eligible (flag OR skill) total: {len(union_ids)}"),
        )

        # Print a concise list (cap at 50)
        def preview(lst):
            return ", ".join(lst[:50]) + (" …" if len(lst) > 50 else "")

        self.stdout.write("")
        self.stdout.write("Usernames by flag:")
        self.stdout.write(preview(usernames_flag) or "<none>")
        self.stdout.write("")
        self.stdout.write("Usernames by skill:")
        self.stdout.write(preview(usernames_skill) or "<none>")
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Usernames (union):"))
        self.stdout.write(preview(usernames_union) or "<none>")
