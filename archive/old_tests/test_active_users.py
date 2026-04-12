#!/usr/bin/env python3
"""Quick test for active users with roles"""

import os

from dotenv import load_dotenv
from requests_oauthlib import OAuth1Session

load_dotenv()

# Create OAuth session
oauth = OAuth1Session(
    os.getenv('NETSUITE_CONSUMER_KEY'),
    client_secret=os.getenv('NETSUITE_CONSUMER_SECRET'),
    resource_owner_key=os.getenv('NETSUITE_TOKEN_ID'),
    resource_owner_secret=os.getenv('NETSUITE_TOKEN_SECRET'),
    realm=os.getenv('NETSUITE_REALM') or os.getenv('NETSUITE_ACCOUNT_ID'),
    signature_method='HMAC-SHA256'
)

# Request active users only
response = oauth.post(
    os.getenv('NETSUITE_RESTLET_URL'),
    json={
        'status': 'ACTIVE',
        'limit': 20,
        'includePermissions': False
    },
    headers={'Content-Type': 'application/json'}
)

data = response.json()

if data.get('success'):
    users = data['data']['users']
    metadata = data['data']['metadata']

    print("\n✓ Success!")
    print(f"Total Users: {metadata['total_users']}")
    print(f"Returned: {metadata['returned_count']}")
    print(f"Execution Time: {metadata['execution_time_seconds']}s\n")

    print("Active Users with Roles:")
    print("-" * 80)

    active_with_roles = [u for u in users if u['status'] == 'ACTIVE' and u['roles_count'] > 0]

    if active_with_roles:
        for user in active_with_roles[:10]:
            print(f"{user['name']:<30} {user['email']:<35} Roles: {user['roles_count']}")
    else:
        print("\nShowing all returned users:")
        for user in users[:10]:
            print(f"{user['name']:<30} {user['email']:<35} Status: {user['status']:<10} Roles: {user['roles_count']}")
else:
    print(f"Error: {data.get('error')}")
    print(f"Message: {data.get('message')}")
