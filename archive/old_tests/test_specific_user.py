#!/usr/bin/env python3
"""Test specific user with roles"""

import os

from dotenv import load_dotenv
from requests_oauthlib import OAuth1Session

load_dotenv()

oauth = OAuth1Session(
    os.getenv('NETSUITE_CONSUMER_KEY'),
    client_secret=os.getenv('NETSUITE_CONSUMER_SECRET'),
    resource_owner_key=os.getenv('NETSUITE_TOKEN_ID'),
    resource_owner_secret=os.getenv('NETSUITE_TOKEN_SECRET'),
    realm=os.getenv('NETSUITE_REALM') or os.getenv('NETSUITE_ACCOUNT_ID'),
    signature_method='HMAC-SHA256'
)

# Search for specific user
print("Searching for robin.turner@fivetran.com with roles...\n")

response = oauth.post(
    os.getenv('NETSUITE_RESTLET_URL'),
    json={
        'status': 'ACTIVE',
        'limit': 1000,  # Get more users to find Robin
        'includePermissions': True
    },
    headers={'Content-Type': 'application/json'}
)

data = response.json()

if data.get('success'):
    users = data['data']['users']

    # Find Robin Turner
    robin = None
    for user in users:
        if 'robin.turner' in user['email'].lower():
            robin = user
            break

    if robin:
        print("✓ Found Robin Turner!")
        print("=" * 80)
        print(f"User ID: {robin['user_id']}")
        print(f"Internal ID: {robin['internal_id']}")
        print(f"Name: {robin['name']}")
        print(f"Email: {robin['email']}")
        print(f"Status: {robin['status']}")
        print(f"Subsidiary: {robin.get('subsidiary', 'N/A')}")
        print(f"Department: {robin.get('department', 'N/A')}")
        print(f"Roles Count: {robin['roles_count']}")
        print()

        if robin['roles']:
            print("Roles:")
            for role in robin['roles']:
                print(f"\n  Role: {role['role_name']}")
                print(f"  Role ID: {role['role_id']}")
                print(f"  Is Custom: {role.get('is_custom', 'N/A')}")

                if 'permissions' in role and role['permissions']:
                    print(f"  Permissions ({len(role['permissions'])}):")
                    for perm in role['permissions'][:10]:  # Show first 10
                        print(f"    - {perm['permission']}: {perm['level']}")
                    if len(role['permissions']) > 10:
                        print(f"    ... and {len(role['permissions']) - 10} more")
        else:
            print("⚠ No roles found for this user in the response")
            print("\nThis suggests the getUserRoles function in the RESTlet isn't working.")
    else:
        print("✗ Robin Turner not found in the first 1000 users")
        print(f"Total users returned: {len(users)}")

        # Show some user emails for debugging
        print("\nSample of returned emails:")
        for user in users[:10]:
            print(f"  - {user['email']}")
else:
    print(f"✗ Error: {data.get('error')}")
    print(f"Message: {data.get('message')}")
