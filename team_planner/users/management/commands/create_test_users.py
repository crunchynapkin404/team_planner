from django.core.management.base import BaseCommand
from django.db import connections

from team_planner.users.models import User


class Command(BaseCommand):
    help = "Create test users in the PostgreSQL database used by HTTP server"

    def handle(self, *args, **options):
        # Force using the default database
        db_alias = "default"

        # Check which database we're using
        connection = connections[db_alias]
        self.stdout.write(f"Database engine: {connection.vendor}")
        self.stdout.write(f"Database name: {connection.settings_dict['NAME']}")
        self.stdout.write(f"Database host: {connection.settings_dict['HOST']}")

        # Create users explicitly in the PostgreSQL database
        try:
            user1, created1 = User.objects.using(db_alias).get_or_create(
                username="simpletest",
                defaults={"email": "test@example.com", "is_active": True},
            )
            if created1:
                user1.set_password("test")
                user1.save(using=db_alias)
                self.stdout.write(f"Created user: {user1.username}")
            else:
                self.stdout.write(f"User already exists: {user1.username}")

            user2, created2 = User.objects.using(db_alias).get_or_create(
                username="admin",
                defaults={
                    "email": "admin@test.com",
                    "is_staff": True,
                    "is_superuser": True,
                    "is_active": True,
                },
            )
            if created2:
                user2.set_password("admin")
                user2.save(using=db_alias)
                self.stdout.write(f"Created admin user: {user2.username}")
            else:
                self.stdout.write(f"Admin user already exists: {user2.username}")

            # Show all users in this database
            all_users = User.objects.using(db_alias).all()
            self.stdout.write(f"Total users in database: {all_users.count()}")
            for user in all_users:
                self.stdout.write(f"  - {user.username} (active: {user.is_active})")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {e}"))
