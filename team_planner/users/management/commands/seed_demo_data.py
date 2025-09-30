from django.core.management.base import BaseCommand
from django.db import transaction

from team_planner.utils.seeding import seed_demo_data


class Command(BaseCommand):
    help = "Seed demo department, team, skills, and users for frontend testing"

    def add_arguments(self, parser):
        parser.add_argument("--department", type=str, default="Operations")
        parser.add_argument("--team", type=str, default="A-Team")
        parser.add_argument("--count", type=int, default=12)
        parser.add_argument("--prefix", type=str, default="demo")
        parser.add_argument("--password", type=str, default="ComplexPassword123!")
        parser.add_argument("--reset", action="store_true")
        parser.add_argument("--create-admin", action="store_true")
        parser.add_argument("--admin-username", type=str, default="admin")
        parser.add_argument("--admin-password", type=str, default="AdminPassword123!")

    @transaction.atomic
    def handle(self, *args, **options):
        s = seed_demo_data(
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
        self.stdout.write(self.style.SUCCESS("Demo data ready"))
        self.stdout.write(f"Department: {s.department}")
        self.stdout.write(f"Team: {s.team} (id={s.team_id})")
        self.stdout.write(
            f"Users processed: {s.count} (created: {s.created}, untouched/updated: {s.updated})",
        )
        c = s.categories
        self.stdout.write(
            f"Categories => incidents_only: {c['incidents_only']}, waakdienst_only: {c['waakdienst_only']}, both: {c['both']}, neither: {c['neither']}",
        )
        self.stdout.write("Usernames (first 6): " + ", ".join(s.usernames[:6]))
        self.stdout.write(f"Password: {s.password}")
        if s.admin_username:
            self.stdout.write(f"Admin: {s.admin_username}")
