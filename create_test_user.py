#!/usr/bin/env python
import os
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token

User = get_user_model()

# Create a test user
username = 'testuser'
email = 'test@example.com'
password = 'testpass123'

# Delete existing user if exists
if User.objects.filter(username=username).exists():
    User.objects.filter(username=username).delete()
    print(f"Deleted existing user: {username}")

# Create new user
user = User.objects.create_user(
    username=username,
    email=email,
    password=password
)

# Create or get token for the user
token, created = Token.objects.get_or_create(user=user)

print(f"Created user: {username}")
print(f"Email: {email}")
print(f"Password: {password}")
print(f"Token: {token.key}")
print("\nYou can now use these credentials to log in to the frontend!")
