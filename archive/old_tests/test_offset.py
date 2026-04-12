#!/usr/bin/env python3
"""Test with offset to skip past inactive users"""

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

# Try with different offsets
for offset in [0, 100, 500, 1000]:
    print(f"\n=== Testing with offset: {offset} ===")

    response = oauth.post(
        os.getenv('NETSUITE_RESTLET_URL'),
        json={
            'status': 'ACTIVE',
            'limit': 10,
            'offset': offset,
            'includePermissions': False
        },
        headers={'Content-Type': 'application/json'}
    )

    data = response.json()

    if data.get('success'):
        users = data['data']['users']

        print(f"Returned: {len(users)} users")

        active_count = sum(1 for u in users if u['status'] == 'ACTIVE')
        with_roles = sum(1 for u in users if u['roles_count'] > 0)

        print(f"  Active: {active_count}")
        print(f"  With Roles: {with_roles}")

        if active_count > 0 or with_roles > 0:
            print("\nSample users:")
            for user in users[:3]:
                print(f"  {user['name']:<30} Status: {user['status']:<10} Roles: {user['roles_count']}")
