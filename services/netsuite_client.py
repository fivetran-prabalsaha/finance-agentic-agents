"""
NetSuite OAuth 1.0a Client for RESTlet API calls

Provides authenticated access to NetSuite RESTlet endpoints
with automatic OAuth signature generation.
"""

import logging
import os
from datetime import datetime
from typing import Any

from dotenv import load_dotenv
from requests_oauthlib import OAuth1Session

load_dotenv()

logger = logging.getLogger(__name__)


class NetSuiteClient:
    """Client for authenticated NetSuite RESTlet API calls"""

    def __init__(
        self,
        consumer_key: str | None = None,
        consumer_secret: str | None = None,
        token_id: str | None = None,
        token_secret: str | None = None,
        realm: str | None = None,
        restlet_url: str | None = None
    ):
        """
        Initialize NetSuite client with OAuth 1.0a credentials

        Args:
            consumer_key: NetSuite Consumer Key (from Integration Record)
            consumer_secret: NetSuite Consumer Secret
            token_id: Token ID (from Access Token)
            token_secret: Token Secret
            realm: NetSuite Account ID (e.g., '5260239_SB1')
            restlet_url: Full RESTlet URL with script and deploy params
        """
        self.consumer_key = consumer_key or os.getenv('NETSUITE_CONSUMER_KEY')
        self.consumer_secret = consumer_secret or os.getenv('NETSUITE_CONSUMER_SECRET')
        self.token_id = token_id or os.getenv('NETSUITE_TOKEN_ID')
        self.token_secret = token_secret or os.getenv('NETSUITE_TOKEN_SECRET')
        self.realm = realm or os.getenv('NETSUITE_REALM')
        self.restlet_url = restlet_url or os.getenv('NETSUITE_RESTLET_URL')

        # Validate credentials
        if not all([self.consumer_key, self.consumer_secret, self.token_id, self.token_secret, self.realm]):
            raise ValueError("Missing NetSuite credentials. Check environment variables.")

        # Create OAuth session
        self.session = OAuth1Session(
            self.consumer_key,
            client_secret=self.consumer_secret,
            resource_owner_key=self.token_id,
            resource_owner_secret=self.token_secret,
            realm=self.realm,
            signature_method='HMAC-SHA256'
        )

        logger.info(f"NetSuite client initialized for realm: {self.realm}")

    def get_users_and_roles(
        self,
        status: str = 'ACTIVE',
        subsidiary: str | None = None,
        department: str | None = None,
        limit: int = 1000,
        offset: int = 0,
        include_permissions: bool = True,
        include_inactive: bool = False,
        last_modified_after: datetime | None = None
    ) -> dict[str, Any]:
        """
        Fetch users and their roles from NetSuite

        Args:
            status: Filter by status ('ACTIVE' or 'INACTIVE')
            subsidiary: Filter by subsidiary name
            department: Filter by department name
            limit: Maximum number of users to return
            offset: Pagination offset
            include_permissions: Include detailed role permissions
            include_inactive: Include inactive users in results
            last_modified_after: Only return users modified after this datetime (incremental sync)

        Returns:
            Dict with 'success', 'data', and optional 'error' keys
            data contains 'users' list and 'metadata' dict
        """
        payload = {
            'status': status,
            'limit': limit,
            'offset': offset,
            'includePermissions': include_permissions,
            'includeInactive': include_inactive
        }

        if subsidiary:
            payload['subsidiary'] = subsidiary

        if department:
            payload['department'] = department

        if last_modified_after:
            payload['lastModifiedDate'] = last_modified_after.strftime('%m/%d/%Y %H:%M:%S')

        try:
            logger.info(f"Fetching users: limit={limit}, offset={offset}, status={status}")

            response = self.session.post(
                self.restlet_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=60
            )

            response.raise_for_status()
            data = response.json()

            if data.get('success'):
                users_count = len(data['data']['users'])
                logger.info(f"Successfully fetched {users_count} users")
            else:
                logger.error(f"NetSuite error: {data.get('error')}")

            return data

        except Exception as e:
            logger.error(f"Error fetching users from NetSuite: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to fetch users from NetSuite'
            }

    def get_all_users_paginated(
        self,
        include_permissions: bool = True,
        status: str = 'ACTIVE',
        page_size: int = 1000,
        last_modified_after: datetime | None = None
    ) -> dict[str, Any]:
        """
        Fetch all users with automatic pagination

        Args:
            include_permissions: Include detailed role permissions
            status: Filter by status
            page_size: Number of users per page
            last_modified_after: Only return users modified after this datetime (incremental sync)

        Returns:
            Dict with all users combined from multiple pages
        """
        all_users = []
        offset = 0
        total_fetched = 0

        logger.info("Starting paginated fetch of all users")

        while True:
            result = self.get_users_and_roles(
                status=status,
                limit=page_size,
                offset=offset,
                include_permissions=include_permissions,
                last_modified_after=last_modified_after
            )

            if not result.get('success'):
                logger.error(f"Pagination failed at offset {offset}")
                break

            users = result['data']['users']
            all_users.extend(users)
            total_fetched += len(users)

            metadata = result['data']['metadata']
            logger.info(f"Fetched page: {total_fetched}/{metadata['total_users']} users")

            # Check if there are more pages
            if not metadata.get('has_more'):
                break

            offset += page_size

        logger.info(f"Pagination complete: {len(all_users)} total users fetched")

        return {
            'success': True,
            'data': {
                'users': all_users,
                'metadata': {
                    'total_users': len(all_users),
                    'returned_count': len(all_users),
                    'status': status
                }
            }
        }

    def get_user_by_email(self, email: str, include_permissions: bool = True) -> dict[str, Any] | None:
        """
        Find a specific user by email address

        Args:
            email: User's email address
            include_permissions: Include role permissions

        Returns:
            User dict if found, None otherwise
        """
        logger.info(f"Searching for user: {email}")

        result = self.get_users_and_roles(
            limit=1000,
            include_permissions=include_permissions
        )

        if not result.get('success'):
            logger.error(f"Failed to search for user: {email}")
            return None

        users = result['data']['users']
        for user in users:
            if user.get('email', '').lower() == email.lower():
                logger.info(f"Found user: {user['name']}")
                return user

        logger.warning(f"User not found: {email}")
        return None

    def search_users(
        self,
        search_value: str,
        search_type: str = 'both',
        include_permissions: bool = True,
        include_inactive: bool = False,
        search_restlet_url: str | None = None
    ) -> dict[str, Any]:
        """
        Search for specific users by name or email using dedicated search RESTlet

        This is much faster and more efficient than fetching all users.
        Uses NetSuite saved search with wildcards for targeted user lookup.

        Args:
            search_value: Name (e.g., "John Doe") or email (e.g., "john@company.com")
            search_type: 'name', 'email', or 'both' (default)
            include_permissions: Include detailed role permissions
            include_inactive: Include inactive users in results
            search_restlet_url: URL for search RESTlet (defaults to NETSUITE_SEARCH_RESTLET_URL env var)

        Returns:
            Dict with 'success', 'data', and optional 'error' keys
            data contains 'users' list and 'metadata' dict

        Example:
            # Search by name
            result = client.search_users("John Doe", search_type="name")

            # Search by email
            result = client.search_users("john.doe@company.com", search_type="email")

            # Search by either (default)
            result = client.search_users("John", search_type="both")
        """
        # Use dedicated search RESTlet URL if available
        if search_restlet_url is None:
            search_restlet_url = os.getenv('NETSUITE_SEARCH_RESTLET_URL')

        # Fall back to main RESTlet if search RESTlet not configured
        if not search_restlet_url:
            logger.warning("NETSUITE_SEARCH_RESTLET_URL not configured, falling back to get_user_by_email")
            # Fallback to old method
            if search_type == 'email' or '@' in search_value:
                user = self.get_user_by_email(search_value, include_permissions)
                if user:
                    return {
                        'success': True,
                        'data': {
                            'users': [user],
                            'metadata': {
                                'search_value': search_value,
                                'users_found': 1
                            }
                        }
                    }
            return {
                'success': False,
                'error': 'Search RESTlet not configured and fallback search failed'
            }

        payload = {
            'searchType': search_type,
            'searchValue': search_value,
            'includePermissions': include_permissions,
            'includeInactive': include_inactive
        }

        try:
            logger.info(f"Searching users: value='{search_value}', type={search_type}")

            response = self.session.post(
                search_restlet_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=60
            )

            response.raise_for_status()
            data = response.json()

            if data.get('success'):
                users_found = len(data['data']['users'])
                logger.info(f"✓ Found {users_found} user(s) matching '{search_value}'")
            else:
                logger.error(f"NetSuite search error: {data.get('error')}")

            return data

        except Exception as e:
            logger.error(f"Error searching users in NetSuite: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': f'Failed to search for users matching "{search_value}"'
            }

    def test_connection(self) -> bool:
        """
        Test the NetSuite connection with a minimal API call

        Returns:
            True if connection is successful, False otherwise
        """
        try:
            logger.info("Testing NetSuite connection...")
            result = self.get_users_and_roles(limit=1, include_permissions=False)

            if result.get('success'):
                logger.info("✓ Connection test successful")
                return True
            else:
                logger.error(f"✗ Connection test failed: {result.get('error')}")
                return False

        except Exception as e:
            logger.error(f"✗ Connection test failed with exception: {str(e)}")
            return False


# Convenience function for quick access
def get_netsuite_client() -> NetSuiteClient:
    """Get a configured NetSuite client instance"""
    return NetSuiteClient()
