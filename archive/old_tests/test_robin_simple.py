#!/usr/bin/env python3
"""Test Robin without permissions to debug"""

import os

from dotenv import load_dotenv
from requests_oauthlib import OAuth1Session

load_dotenv()

oauth = OAuth1Session(
    os.getenv('NETSUITE_CONSUMER_KEY'),
    client_secret=os.getenv('NETSUITE_CONSUMER_SECRET'),
    resource_owner_key=os.getenv('NETSUITE_TOKEN_ID'),
    resource_owner_secret=os.getenv('NETSUITE_TOKEN_SECRET'),
    realm=os.getenv('NETSUITE_REALM'),
    signature_method='HMAC-SHA256'
)

print("Fetching users WITHOUT permissions...\n")

response = oauth.post(
    os.getenv('NETSUITE_RESTLET_URL'),
    json={
        'limit': 1000,
        'includePermissions': False  # Don't fetch permissions
    },
    headers={'Content-Type': 'application/json'}
)

data = response.json()

if data.get('success'):
    users = data['data']['users']
    print(f"✓ Fetched {len(users)} users")

    # Find Robin
    robin = next((u for u in users if 'robin.turner' in u['email'].lower()), None)

    if robin:
        print("\n✓ Found Robin Turner!")
        print("=" * 60)
        print(f"User ID: {robin['user_id']}")
        print(f"Name: {robin['name']}")
        print(f"Email: {robin['email']}")
        print(f"Status: {robin['status']}")
        print(f"Roles Count: {robin['roles_count']}")
        print()

        if robin['roles']:
            print("Roles (without permissions):")
            for role in robin['roles']:
                print(f"  - {role['role_name']} (ID: {role['role_id']})")
        else:
            print("⚠ No roles found")
            print("\nThe getUserRoles function needs debugging.")
    else:
        print("\n✗ Robin not found")
        print(f"Searched {len(users)} users")
else:
    print(f"✗ Error: {data.get('error')}")
    print(f"Message: {data.get('message')}")
