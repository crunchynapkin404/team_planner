"""
Management command to create Team 7 with engineers and their shift type skills.

This creates the team data based on the actual shift types the orchestrator expects:
- incidents (incidents shift skill)
- waakdienst (waakdienst shift skill)

Usage:
    python manage.py create_team7
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

from team_planner.teams.models import Team, Department, TeamMembership
from team_planner.employees.models import EmployeeProfile, EmployeeSkill
from team_planner.shifts.models import ShiftType

User = get_user_model()


class Command(BaseCommand):
    help = 'Create Team 7 with engineers and their shift type skills'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually creating it',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        # Team 7 engineers with their shift type skills
        team_data = {
            'team_name': 'Team 7',
            'engineers': [
                {
                    'first_name': 'Renee',
                    'last_name': 'Kanters',
                    'username': 'renee.kanters',
                    'email': 'renee.kanters@company.com',
                    'shift_types': ['incidents']  # incidents skill
                },
                {
                    'first_name': 'Bart',
                    'last_name': 'Abraas', 
                    'username': 'bart.abraas',
                    'email': 'bart.abraas@company.com',
                    'shift_types': ['incidents', 'waakdienst']  # both skills
                },
                {
                    'first_name': 'Egied',
                    'last_name': 'Custers',
                    'username': 'egied.custers',
                    'email': 'egied.custers@company.com', 
                    'shift_types': ['waakdienst']  # waakdienst skill
                },
                {
                    'first_name': 'Rob',
                    'last_name': 'Dekkers',
                    'username': 'rob.dekkers',
                    'email': 'rob.dekkers@company.com',
                    'shift_types': ['incidents', 'waakdienst']  # both skills
                },
                {
                    'first_name': 'Marc',
                    'last_name': 'Erkens',
                    'username': 'marc.erkens',
                    'email': 'marc.erkens@company.com',
                    'shift_types': ['waakdienst']  # waakdienst skill
                },
                {
                    'first_name': 'Pascal',
                    'last_name': 'Lacroix',
                    'username': 'pascal.lacroix',
                    'email': 'pascal.lacroix@company.com',
                    'shift_types': ['waakdienst']  # waakdienst skill
                },
                {
                    'first_name': 'Patrick',
                    'last_name': 'Rooden',
                    'username': 'patrick.rooden',
                    'email': 'patrick.rooden@company.com',
                    'shift_types': ['waakdienst']  # waakdienst skill
                },
                {
                    'first_name': 'Rik',
                    'last_name': 'van der Mark',
                    'username': 'rik.vandermark',
                    'email': 'rik.vandermark@company.com',
                    'shift_types': ['incidents', 'waakdienst']  # both skills
                },
                {
                    'first_name': 'Nathan',
                    'last_name': 'Monteyne',
                    'username': 'nathan.monteyne',
                    'email': 'nathan.monteyne@company.com',
                    'shift_types': ['incidents']  # incidents skill
                },
                {
                    'first_name': 'Bart',
                    'last_name': 'Constant',
                    'username': 'bart.constant',
                    'email': 'bart.constant@company.com',
                    'shift_types': ['incidents']  # incidents skill
                },
                {
                    'first_name': 'Kevin',
                    'last_name': 'Beenkens',
                    'username': 'kevin.beenkens',
                    'email': 'kevin.beenkens@company.com',
                    'shift_types': []  # no specific shift skills listed
                }
            ]
        }

        try:
            with transaction.atomic():
                # Create skills based on shift types (if they don't exist)
                skills_created = self._create_shift_type_skills(dry_run)
                
                # Create team
                team = self._create_team(team_data['team_name'], dry_run)
                
                # Create engineers and assign to team
                engineers_created = self._create_engineers(team, team_data['engineers'], dry_run)
                
                if dry_run:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'\nDRY RUN COMPLETE:\n'
                            f'Would create {len(skills_created)} skills\n'
                            f'Would create team: {team_data["team_name"]}\n'
                            f'Would create {len(engineers_created)} engineers\n'
                        )
                    )
                    raise transaction.TransactionManagementError("Dry run - rolling back")
                else:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'\nSUCCESSFULLY CREATED:\n'
                            f'✓ {len(skills_created)} skills\n'
                            f'✓ Team: {team.name if team else "None"}\n'
                            f'✓ {len(engineers_created)} engineers\n'
                        )
                    )
        
        except transaction.TransactionManagementError:
            if not dry_run:
                raise

    def _create_shift_type_skills(self, dry_run=False):
        """Create EmployeeSkills based on ShiftType choices."""
        skills_created = []
        
        # Create skills for incidents and waakdienst (the ones actually used in the orchestrator)
        shift_types_to_create = [
            ('incidents', 'Incidents - Monday to Friday 8:00-17:00'),
            ('waakdienst', 'Waakdienst - On-call/standby shifts (evenings, nights, weekends)'),
        ]
        
        for skill_name, description in shift_types_to_create:
            if dry_run:
                existing = EmployeeSkill.objects.filter(name=skill_name).exists()
                if not existing:
                    skills_created.append(skill_name)
                    self.stdout.write(f'Would create skill: {skill_name}')
                else:
                    self.stdout.write(f'Skill already exists: {skill_name}')
            else:
                skill, created = EmployeeSkill.objects.get_or_create(
                    name=skill_name,
                    defaults={'description': description}
                )
                if created:
                    skills_created.append(skill_name)
                    self.stdout.write(f'Created skill: {skill.name}')
                else:
                    self.stdout.write(f'Skill already exists: {skill.name}')
        
        return skills_created

    def _create_team(self, team_name, dry_run=False):
        """Create the team."""
        if dry_run:
            existing = Team.objects.filter(name=team_name).exists()
            if not existing:
                self.stdout.write(f'Would create team: {team_name}')
            else:
                self.stdout.write(f'Team already exists: {team_name}')
            return None
        else:
            # Create default department if needed
            department, _ = Department.objects.get_or_create(
                name='Engineering',
                defaults={'description': 'Engineering Department'}
            )
            
            team, created = Team.objects.get_or_create(
                name=team_name,
                department=department,
                defaults={'description': f'{team_name} - Engineering team with incident and waakdienst capabilities'}
            )
            if created:
                self.stdout.write(f'Created team: {team.name}')
            else:
                self.stdout.write(f'Team already exists: {team.name}')
            return team

    def _create_engineers(self, team, engineers_data, dry_run=False):
        """Create engineers and assign skills."""
        engineers_created = []
        
        for engineer_data in engineers_data:
            if dry_run:
                existing = User.objects.filter(username=engineer_data['username']).exists()
                if not existing:
                    engineers_created.append(engineer_data['username'])
                    self.stdout.write(
                        f'Would create engineer: {engineer_data["first_name"]} {engineer_data["last_name"]} '
                        f'with skills: {", ".join(engineer_data["shift_types"]) or "none"}'
                    )
                else:
                    self.stdout.write(f'Engineer already exists: {engineer_data["username"]}')
            else:
                # Create user
                user, created = User.objects.get_or_create(
                    username=engineer_data['username'],
                    defaults={
                        'name': f"{engineer_data['first_name']} {engineer_data['last_name']}",
                        'email': engineer_data['email'],
                    }
                )
                
                if created:
                    engineers_created.append(engineer_data['username'])
                    self.stdout.write(f'Created user: {user.username}')
                else:
                    self.stdout.write(f'User already exists: {user.username}')
                
                # Create employee profile
                profile, profile_created = EmployeeProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        'employee_id': f'EMP{user.pk:03d}',
                        'hire_date': '2024-01-01',
                        'employment_type': EmployeeProfile.EmploymentType.FULL_TIME,
                        'available_for_incidents': 'incidents' in engineer_data['shift_types'],
                        'available_for_waakdienst': 'waakdienst' in engineer_data['shift_types'],
                    }
                )
                
                if profile_created:
                    self.stdout.write(f'Created profile for: {user.username}')
                else:
                    # Update availability flags if profile exists
                    profile.available_for_incidents = 'incidents' in engineer_data['shift_types']
                    profile.available_for_waakdienst = 'waakdienst' in engineer_data['shift_types']
                    profile.save()
                    self.stdout.write(f'Updated profile for: {user.username}')
                
                # Add to team using TeamMembership
                if team:
                    membership, membership_created = TeamMembership.objects.get_or_create(
                        user=user,
                        team=team,
                        defaults={'role': TeamMembership.Role.MEMBER}
                    )
                    if membership_created:
                        self.stdout.write(f'Added {user.username} to {team.name}')
                    else:
                        self.stdout.write(f'{user.username} already in {team.name}')
                
                # Assign skills
                for shift_type in engineer_data['shift_types']:
                    try:
                        skill = EmployeeSkill.objects.get(name=shift_type)
                        if skill not in profile.skills.all():
                            profile.skills.add(skill)
                            self.stdout.write(f'Added {shift_type} skill to {user.username}')
                    except EmployeeSkill.DoesNotExist:
                        self.stdout.write(
                            self.style.WARNING(f'Skill "{shift_type}" not found for {user.username}')
                        )
        
        return engineers_created
