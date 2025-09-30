from django.core.management.base import BaseCommand
from django.db import transaction

from team_planner.utils.seeding import seed_demo_data


class Command(BaseCommand):
    help = "Seed demo department, team, skills, and users with varied availability/skills for frontend testing"

    def add_arguments(self, parser):
        parser.add_argument(
            "--department",
            type=str,
            default="Operations",
            help="Department name to create/use",
        )
        parser.add_argument(
            "--team", type=str, default="A-Team", help="Team name to create/use",
        )
        parser.add_argument(
            "--count", type=int, default=12, help="How many demo users to create/update",
        )
        parser.add_argument(
            "--prefix",
            type=str,
            default="demo",
            help="Username prefix (usernames will be <prefix><nn>)",
        )
        parser.add_argument(
            "--password",
            type=str,
            default="ComplexPassword123!",
            help="Password to set for all demo users",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="If passed, reset skills/availability for existing users in this batch",
        )
        parser.add_argument(
            "--create-admin",
            action="store_true",
            help="Also create an admin/superuser account",
        )
        parser.add_argument(
            "--admin-username",
            type=str,
            default="admin",
            help="Admin username when using --create-admin",
        )
        parser.add_argument(
            "--admin-password",
            type=str,
            default="AdminPassword123!",
            help="Admin password when using --create-admin",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        summary = seed_demo_data(
            dept_name=options["department"],
            team_name=options["team"],
            count=options["count"],
            prefix=options["prefix"],
            password=options["password"],
            reset=options["reset"],
            create_admin=options["create_admin"],
            admin_username=options["admin_username"],
            admin_password=options["admin_password"],
        )

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Demo data ready"))
        self.stdout.write(f"Department: {summary.department}")
        self.stdout.write(f"Team: {summary.team} (id={summary.team_id})")
        self.stdout.write(
            f"Users processed: {summary.count} (created: {summary.created}, untouched/updated: {summary.updated})",
        )
        cats = summary.categories
        self.stdout.write(
            f"Categories => incidents_only: {cats['incidents_only']}, waakdienst_only: {cats['waakdienst_only']}, both: {cats['both']}, neither: {cats['neither']}",
        )
        self.stdout.write("")
        preview = ", ".join(summary.usernames[:6])
        self.stdout.write("Log in with any of these usernames and the shared password:")
        self.stdout.write(f"  Usernames: {preview}{' …' if summary.count > 6 else ''}")
        self.stdout.write(f"  Password: {summary.password}")
        if summary.admin_username:
            self.stdout.write(f"Admin: {summary.admin_username}")
        self.stdout.write("")
        self.stdout.write("Tip: To get an API token:")
        self.stdout.write(
            '  POST /api/auth-token/ with {"username": <name>, "password": <password>}',
        )
