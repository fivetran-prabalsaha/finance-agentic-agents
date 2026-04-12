#!/usr/bin/env python3
"""
Test NetSuite RESTlet - Verify connectivity and data retrieval

This script tests the deployed NetSuite RESTlet to ensure it's working correctly.

Usage:
    python netsuite/test_restlet.py
    python netsuite/test_restlet.py --limit 5
    python netsuite/test_restlet.py --no-permissions
    python netsuite/test_restlet.py --subsidiary "United States"
"""

import argparse
import json
import os
import sys
from datetime import datetime

try:
    from dotenv import load_dotenv
    from requests_oauthlib import OAuth1Session
except ImportError:
    print("Error: Required packages not installed")
    print("Run: poetry install")
    print("Or: pip install requests-oauthlib python-dotenv")
    sys.exit(1)

# Colors for terminal output
GREEN = '\033[0;32m'
RED = '\033[0;31m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'

def print_success(msg):
    print(f"{GREEN}✓ {msg}{NC}")

def print_error(msg):
    print(f"{RED}✗ {msg}{NC}")

def print_warning(msg):
    print(f"{YELLOW}⚠ {msg}{NC}")

def print_info(msg):
    print(f"{BLUE}ℹ {msg}{NC}")

def print_header(msg):
    print(f"\n{BLUE}{'=' * 60}{NC}")
    print(f"{BLUE}{msg}{NC}")
    print(f"{BLUE}{'=' * 60}{NC}\n")

def load_config():
    """Load NetSuite configuration from .env"""
    load_dotenv()

    config = {
        'account_id': os.getenv('NETSUITE_ACCOUNT_ID'),
        'realm': os.getenv('NETSUITE_REALM') or os.getenv('NETSUITE_ACCOUNT_ID'),
        'consumer_key': os.getenv('NETSUITE_CONSUMER_KEY'),
        'consumer_secret': os.getenv('NETSUITE_CONSUMER_SECRET'),
        'token_id': os.getenv('NETSUITE_TOKEN_ID'),
        'token_secret': os.getenv('NETSUITE_TOKEN_SECRET'),
        'restlet_url': os.getenv('NETSUITE_RESTLET_URL'),
    }

    # Validate config
    missing = [k for k, v in config.items() if not v]
    if missing:
        print_error("Missing required environment variables:")
        for key in missing:
            print(f"  - {key.upper()}")
        print_info("\nAdd these to your .env file")
        sys.exit(1)

    return config

def create_oauth_session(config):
    """Create OAuth 1.0a session for NetSuite"""
    return OAuth1Session(
        config['consumer_key'],
        client_secret=config['consumer_secret'],
        resource_owner_key=config['token_id'],
        resource_owner_secret=config['token_secret'],
        realm=config['realm'],
        signature_method='HMAC-SHA256'
    )

def test_restlet_connection(oauth, url):
    """Test basic connectivity to RESTlet"""
    print_header("Testing RESTlet Connection")

    try:
        print_info(f"Connecting to: {url}")

        # Simple test request
        response = oauth.post(
            url,
            json={'limit': 1, 'includePermissions': False},
            headers={'Content-Type': 'application/json'}
        )

        if response.status_code == 200:
            print_success("Connection successful")
            return True
        else:
            print_error(f"Connection failed: HTTP {response.status_code}")
            print(f"Response: {response.text}")
            return False

    except Exception as e:
        print_error(f"Connection error: {e}")
        return False

def fetch_users(oauth, url, params):
    """Fetch users from RESTlet"""
    print_header("Fetching Users from NetSuite")

    print_info(f"Request parameters: {json.dumps(params, indent=2)}")

    try:
        start_time = datetime.now()

        response = oauth.post(
            url,
            json=params,
            headers={'Content-Type': 'application/json'}
        )

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        if response.status_code != 200:
            print_error(f"Request failed: HTTP {response.status_code}")
            print(f"Response: {response.text}")
            return None

        data = response.json()

        if not data.get('success'):
            print_error("RESTlet returned error")
            print(f"Error: {data.get('error', 'Unknown error')}")
            print(f"Message: {data.get('message', 'No message')}")
            return None

        print_success(f"Request completed in {duration:.2f} seconds")
        return data

    except Exception as e:
        print_error(f"Request error: {e}")
        return None

def display_results(data):
    """Display fetched user data"""
    print_header("Results")

    if not data or not data.get('data'):
        print_warning("No data returned")
        return

    users = data['data'].get('users', [])
    metadata = data['data'].get('metadata', {})

    # Display metadata
    print(f"Total Users: {metadata.get('total_users', 0)}")
    print(f"Returned: {metadata.get('returned_count', 0)}")
    print(f"Has More: {metadata.get('has_more', False)}")
    print(f"Execution Time: {metadata.get('execution_time_seconds', 0):.2f}s")
    print()

    # Display users
    if not users:
        print_warning("No users found")
        return

    print(f"{'User ID':<15} {'Name':<25} {'Email':<30} {'Roles':<5} {'Status':<10}")
    print("-" * 90)

    for user in users:
        print(f"{user['user_id']:<15} "
              f"{user['name']:<25} "
              f"{user['email']:<30} "
              f"{user['roles_count']:<5} "
              f"{user['status']:<10}")

    # Display detailed info for first user
    if users and len(users) > 0:
        print_header("Sample User Details (First User)")
        first_user = users[0]

        print(f"User ID: {first_user['user_id']}")
        print(f"Internal ID: {first_user['internal_id']}")
        print(f"Name: {first_user['name']}")
        print(f"Email: {first_user['email']}")
        print(f"Status: {first_user['status']}")
        print(f"Subsidiary: {first_user.get('subsidiary', 'N/A')}")
        print(f"Department: {first_user.get('department', 'N/A')}")
        print(f"Roles Count: {first_user['roles_count']}")
        print()

        if first_user.get('roles'):
            print("Roles:")
            for role in first_user['roles']:
                perm_info = ""
                if 'permissions' in role:
                    perm_info = f" ({role.get('permission_count', 0)} permissions)"
                custom_marker = " [CUSTOM]" if role.get('is_custom') else ""
                print(f"  • {role['role_name']}{custom_marker}{perm_info}")

                # Show first 5 permissions if available
                if 'permissions' in role and role['permissions']:
                    print("    Permissions (sample):")
                    for perm in role['permissions'][:5]:
                        print(f"      - {perm['permission']}: {perm['level']}")
                    if len(role['permissions']) > 5:
                        print(f"      ... and {len(role['permissions']) - 5} more")

def run_test_suite(oauth, url):
    """Run comprehensive test suite"""
    print_header("RESTlet Test Suite")

    tests = [
        {
            'name': 'Basic Test (5 users, no permissions)',
            'params': {'limit': 5, 'includePermissions': False}
        },
        {
            'name': 'Full Test (5 users with permissions)',
            'params': {'limit': 5, 'includePermissions': True}
        },
        {
            'name': 'Active Users Only',
            'params': {'status': 'ACTIVE', 'limit': 10, 'includePermissions': False}
        },
    ]

    results = []

    for test in tests:
        print_info(f"\nRunning: {test['name']}")
        data = fetch_users(oauth, url, test['params'])

        if data and data.get('success'):
            print_success(f"{test['name']} - PASSED")
            results.append(True)
        else:
            print_error(f"{test['name']} - FAILED")
            results.append(False)

    # Summary
    print_header("Test Summary")
    passed = sum(results)
    total = len(results)

    print(f"Tests Passed: {passed}/{total}")

    if passed == total:
        print_success("All tests passed! ✨")
    else:
        print_warning(f"{total - passed} test(s) failed")

    return passed == total

def main():
    parser = argparse.ArgumentParser(description='Test NetSuite RESTlet')
    parser.add_argument('--limit', type=int, default=10, help='Number of users to fetch')
    parser.add_argument('--offset', type=int, default=0, help='Offset for pagination')
    parser.add_argument('--subsidiary', type=str, help='Filter by subsidiary')
    parser.add_argument('--department', type=str, help='Filter by department')
    parser.add_argument('--no-permissions', action='store_true', help='Exclude permissions')
    parser.add_argument('--test-suite', action='store_true', help='Run full test suite')

    args = parser.parse_args()

    print_header("NetSuite RESTlet Test")

    # Load config
    config = load_config()
    print_success("Configuration loaded")

    # Create OAuth session
    oauth = create_oauth_session(config)
    print_success("OAuth session created")

    # Test connection
    if not test_restlet_connection(oauth, config['restlet_url']):
        print_error("Connection test failed")
        sys.exit(1)

    # Run test suite or single request
    if args.test_suite:
        success = run_test_suite(oauth, config['restlet_url'])
        sys.exit(0 if success else 1)
    else:
        # Build request params
        params = {
            'limit': args.limit,
            'offset': args.offset,
            'includePermissions': not args.no_permissions
        }

        if args.subsidiary:
            params['subsidiary'] = args.subsidiary

        if args.department:
            params['department'] = args.department

        # Fetch users
        data = fetch_users(oauth, config['restlet_url'], params)

        if data:
            display_results(data)
            print_success("\nTest completed successfully! ✨")
            sys.exit(0)
        else:
            print_error("\nTest failed")
            sys.exit(1)

if __name__ == '__main__':
    main()
