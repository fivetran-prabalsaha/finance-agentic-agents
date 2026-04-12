"""
Quick utility to list users from NetSuite to find correct names/emails
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.netsuite_client import NetSuiteClient

client = NetSuiteClient()

print("\n📋 Fetching users from NetSuite...\n")

result = client.get_users_and_roles(limit=100, offset=0, include_permissions=False)

if result.get('success'):
    users = result['data']['users']
    print(f"Found {len(users)} users. Showing names and emails:\n")
    print(f"{'#':<4} {'Name':<40} {'Email':<50} {'Roles':>6}")
    print("-" * 105)

    for i, user in enumerate(users, 1):
        name = user.get('name', '').strip() or '[no name]'
        email = user.get('email', '')
        roles = user.get('roles_count', 0)
        print(f"{i:<4} {name:<40} {email:<50} {roles:>6}")

    print("\nSearch for 'Prabal' or 'Robin' in the list above.")
    print("If found, use the exact name or email address for the analysis.\n")
else:
    print(f"Error: {result.get('error')}\n")
