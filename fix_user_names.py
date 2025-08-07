#!/usr/bin/env python
"""
Utility script to fix user names in the Team Planner database.
This script helps resolve the "None None" name issue by properly populating
the name field from usernames or allowing manual input.
"""

import os
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

def auto_fix_user_names():
    """Automatically fix user names from usernames."""
    users = User.objects.all()
    updated_count = 0
    
    print("Checking user names...")
    print("-" * 50)
    
    for user in users:
        print(f"User: {user.username}")
        print(f"  Current name: '{user.name}'")
        print(f"  Full name method: '{user.get_full_name()}'")
        
        if not user.name.strip():
            # Generate name from username
            parts = user.username.replace('.', ' ').replace('_', ' ').replace('-', ' ').split()
            
            if len(parts) >= 2:
                # Multiple parts - capitalize each part
                formatted_name = ' '.join(word.capitalize() for word in parts)
            else:
                # Single part - just capitalize
                formatted_name = user.username.capitalize()
            
            user.name = formatted_name
            user.save()
            print(f"  -> Updated to: '{user.name}'")
            updated_count += 1
        else:
            print(f"  -> Name already set")
        
        print()
    
    print(f"Summary: Updated {updated_count} users")
    return updated_count

def manual_fix_user_names():
    """Manually fix user names with user input."""
    users = User.objects.filter(name__exact='') | User.objects.filter(name__isnull=True)
    
    if not users.exists():
        print("No users found with empty names.")
        return
    
    print(f"Found {users.count()} users with empty names.")
    print("Enter new names (press Enter to skip):")
    print("-" * 50)
    
    for user in users:
        current_suggestion = user.username.replace('.', ' ').replace('_', ' ').title()
        new_name = input(f"Name for '{user.username}' (suggested: {current_suggestion}): ").strip()
        
        if new_name:
            user.name = new_name
            user.save()
            print(f"  Updated to: '{user.name}'")
        else:
            # Use suggested name
            user.name = current_suggestion
            user.save()
            print(f"  Used suggestion: '{user.name}'")

def check_all_users():
    """Check and display all user names."""
    users = User.objects.all().order_by('username')
    
    print("All users and their names:")
    print("-" * 60)
    print(f"{'Username':<20} {'Name':<25} {'Full Name Method'}")
    print("-" * 60)
    
    for user in users:
        print(f"{user.username:<20} {user.name:<25} {user.get_full_name()}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'auto':
            auto_fix_user_names()
        elif command == 'manual':
            manual_fix_user_names()
        elif command == 'check':
            check_all_users()
        else:
            print("Unknown command. Use: auto, manual, or check")
    else:
        print("User Name Fix Utility")
        print("====================")
        print()
        print("Commands:")
        print("  python fix_user_names.py auto   - Automatically fix names from usernames")
        print("  python fix_user_names.py manual - Manually enter names for users")
        print("  python fix_user_names.py check  - Check all user names")
        print()
        
        # Run check by default
        check_all_users()
