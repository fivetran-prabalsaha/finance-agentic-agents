#!/usr/bin/env python3
"""
Quick test of Data Collection Agent
Run this to verify the agent is working correctly
"""

import os
import sys

from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.data_collector import DataCollectionAgent

load_dotenv()

def main():
    print("\n" + "="*60)
    print("  SOD COMPLIANCE - DATA COLLECTION AGENT")
    print("  Quick Test")
    print("="*60 + "\n")

    # Create agent
    print("1. Initializing Data Collection Agent...")
    agent = DataCollectionAgent()
    print("   ✓ Agent initialized\n")

    # Test connection
    print("2. Testing NetSuite connection...")
    if agent.test_connection():
        print("   ✓ Connection successful\n")
    else:
        print("   ✗ Connection failed\n")
        return

    # Fetch sample users
    print("3. Fetching 10 users (with permissions)...")
    result = agent.netsuite_client.get_users_and_roles(
        limit=10,
        include_permissions=True
    )

    if result.get('success'):
        users = result['data']['users']
        metadata = result['data']['metadata']

        print(f"   ✓ Fetched {len(users)} users")
        print(f"   • Total users in system: {metadata['total_users']}")
        print(f"   • Execution time: {metadata['execution_time_seconds']:.2f}s\n")

        if users:
            user = users[0]
            print("   Sample user:")
            print(f"     Name: {user['name']}")
            print(f"     Email: {user['email']}")
            print(f"     Roles: {user['roles_count']}")

            if user.get('roles'):
                role = user['roles'][0]
                perm_count = len(role.get('permissions', []))
                print(f"     First role: {role['role_name']} ({perm_count} permissions)")
    else:
        print(f"   ✗ Error: {result.get('error')}")
        return

    print("\n" + "="*60)
    print("  ✓ Data Collection Agent is working!")
    print("="*60 + "\n")

    print("Next steps:")
    print("  • Run full test suite: python tests/test_data_collector.py")
    print("  • Build database models and storage layer")
    print("  • Create Analysis Agent for SOD violation detection")
    print()


if __name__ == '__main__':
    main()
