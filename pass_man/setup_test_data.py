import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

def create_user(email, password, is_superuser=False):
    if not User.objects.filter(email=email).exists():
        if is_superuser:
            User.objects.create_superuser(email=email, password=password, full_name='Admin User')
        else:
            User.objects.create_user(email=email, password=password, full_name=f'User {email.split("@")[0]}')
        print(f"Created user: {email}")
    else:
        print(f"User exists: {email}")

create_user('admin@passman.com', 'admin', is_superuser=True)
create_user('demo@passman.com', 'password')
create_user('friend@passman.com', 'password')
