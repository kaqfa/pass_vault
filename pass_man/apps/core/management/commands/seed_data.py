import random
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from faker import Faker

from apps.groups.models import Group, UserGroup
from apps.passwords.models import Password

User = get_user_model()

class Command(BaseCommand):
    help = 'Seeds the database with realistic test data'

    def handle(self, *args, **kwargs):
        self.stdout.write('Seeding data...')
        fake = Faker()
        
        # Create Users
        users = []
        self.stdout.write('Creating users...')
        # Create admin user if not exists
        if not User.objects.filter(email='admin@example.com').exists():
            admin = User.objects.create_superuser(
                'admin@example.com', 'adminpassword', full_name='Admin User'
            )
            users.append(admin)
            self.stdout.write(self.style.SUCCESS('Created admin user'))

        # Create demo user if not exists
        if not User.objects.filter(email='demo@passmanager.com').exists():
            demo = User.objects.create_user(
                'demo@passmanager.com', 'DemoPass123!', full_name='Demo User'
            )
            users.append(demo)
            self.stdout.write(self.style.SUCCESS('Created demo user'))
            
        # Create random users
        for _ in range(20):
            email = fake.unique.email()
            if not User.objects.filter(email=email).exists():
                user = User.objects.create_user(
                    email=email,
                    password='password123',
                    full_name=fake.name()
                )
                users.append(user)
        
        self.stdout.write(self.style.SUCCESS(f'Created {len(users)} users'))

        # Create Groups
        self.stdout.write('Creating groups...')
        groups = []
        for i in range(10):
            owner = random.choice(users)
            name = fake.company()
            # Ensure unique name for owner
            while Group.objects.filter(owner=owner, name=name).exists():
                name = fake.company() + f" {random.randint(1, 100)}"
                
            group = Group.objects.create(
                name=name,
                description=fake.catch_phrase(),
                owner=owner,
                is_personal=random.choice([True, False])
            )
            groups.append(group)
            
            # Add owner as member (handled by signal usually, but let's ensure)
            if not UserGroup.objects.filter(user=owner, group=group).exists():
                UserGroup.objects.create(
                    user=owner, 
                    group=group, 
                    role=UserGroup.Role.OWNER
                )

        self.stdout.write(self.style.SUCCESS(f'Created {len(groups)} groups'))

        # Assign Memberships
        self.stdout.write('Assigning memberships...')
        for group in groups:
            # Add random members
            potential_members = [u for u in users if u != group.owner]
            num_members = random.randint(1, 5)
            members_to_add = random.sample(potential_members, min(len(potential_members), num_members))
            
            for member in members_to_add:
                if not UserGroup.objects.filter(user=member, group=group).exists():
                    role = random.choice([UserGroup.Role.ADMIN, UserGroup.Role.MEMBER])
                    UserGroup.objects.create(
                        user=member,
                        group=group,
                        role=role,
                        added_by=group.owner
                    )
        
        self.stdout.write(self.style.SUCCESS('Assigned memberships'))

        # Create Directories
        self.stdout.write('Creating directories...')
        from apps.directories.models import Directory
        
        for group in groups:
            # Create root directories
            root_dirs = []
            for _ in range(random.randint(1, 3)):
                root_dir = Directory.objects.create(
                    name=fake.bs().split()[0].capitalize() + " Folder",
                    description=fake.catch_phrase(),
                    group=group,
                    created_by=group.owner
                )
                root_dirs.append(root_dir)
                
                # Create subdirectories (depth 1)
                for _ in range(random.randint(0, 2)):
                    Directory.objects.create(
                        name=fake.bs().split()[0].capitalize() + " Subfolder",
                        description=fake.catch_phrase(),
                        parent=root_dir,
                        group=group,
                        created_by=group.owner
                    )
        
        self.stdout.write(self.style.SUCCESS('Directories created'))

        # Create Passwords
        self.stdout.write('Creating passwords...')
        password_count = 0
        from apps.passwords.models import PasswordHistory, PasswordAccessLog
        
        for group in groups:
            # Get group members
            members = group.get_members()
            # Get group directories
            group_dirs = list(Directory.objects.filter(group=group))
            
            # Create 5-10 passwords per group
            for _ in range(random.randint(5, 10)):
                creator = random.choice(members)
                title = fake.bs().title()
                
                # Randomly assign to a directory (50% chance)
                directory = None
                if group_dirs and random.choice([True, False]):
                    directory = random.choice(group_dirs)
                
                password_entry = Password(
                    title=title,
                    username=fake.user_name(),
                    url=fake.url(),
                    notes=fake.text(),
                    group=group,
                    directory=directory,
                    created_by=creator,
                    priority=random.choice(Password.Priority.values),
                    is_favorite=random.choice([True, False]),
                    tags=[fake.word() for _ in range(random.randint(0, 3))]
                )
                
                # Set password (encrypts it)
                password_entry.set_password(fake.password())
                password_entry.save()
                password_count += 1
                
                # Create History - Creation
                PasswordHistory.objects.create(
                    password=password_entry,
                    change_type=PasswordHistory.ChangeType.CREATED,
                    changed_by=creator,
                    previous_values={},
                    change_summary="Initial creation"
                )
                
                # Simulate updates (30% chance)
                if random.random() < 0.3:
                    old_title = password_entry.title
                    password_entry.title = fake.bs().title()
                    password_entry.save()
                    
                    PasswordHistory.objects.create(
                        password=password_entry,
                        change_type=PasswordHistory.ChangeType.UPDATED,
                        changed_by=creator,
                        previous_values={'title': old_title},
                        change_summary="Updated title"
                    )
                
                # Simulate access logs (random 0-5 accesses)
                for _ in range(random.randint(0, 5)):
                    accessor = random.choice(members)
                    password_entry.record_access(user=accessor)

        self.stdout.write(self.style.SUCCESS(f'Created {password_count} passwords'))
        self.stdout.write(self.style.SUCCESS('Database seeding completed successfully!'))
