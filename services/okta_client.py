"""
Okta API Client

Handles authentication and API calls to Okta
"""

import logging
import os
from datetime import datetime
from typing import Any

import requests

logger = logging.getLogger(__name__)


class OktaClient:
    """Client for Okta API integration"""

    def __init__(
        self,
        domain: str | None = None,
        api_token: str | None = None
    ):
        """
        Initialize Okta client

        Args:
            domain: Okta domain (e.g., 'mycompany.okta.com')
            api_token: Okta API token
        """
        self.domain = domain or os.getenv('OKTA_DOMAIN')
        self.api_token = api_token or os.getenv('OKTA_API_TOKEN')

        if not self.domain or not self.api_token:
            raise ValueError("OKTA_DOMAIN and OKTA_API_TOKEN required")

        self.base_url = f"https://{self.domain}/api/v1"
        self.headers = {
            'Authorization': f'SSWS {self.api_token}',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }

    def get_users(
        self,
        status: str | None = None,
        limit: int = 200
    ) -> dict[str, Any]:
        """
        Get users from Okta

        Args:
            status: ACTIVE, DEPROVISIONED, SUSPENDED, etc. (None = all users)
            limit: Results per page (max 200)

        Returns:
            Dict with users list and pagination info
        """
        users = []
        url = f"{self.base_url}/users"
        params = {
            'limit': limit
        }

        if status:
            params['filter'] = f'status eq "{status}"'

        while url:
            try:
                response = requests.get(
                    url,
                    headers=self.headers,
                    params=params if url == f"{self.base_url}/users" else None,
                    timeout=30
                )
                response.raise_for_status()

                batch = response.json()
                users.extend(batch)

                # Check for next page in Link header
                link_header = response.headers.get('Link', '')
                url = self._parse_next_link(link_header)

                logger.info(f"Fetched {len(batch)} users from Okta (total: {len(users)})")

            except requests.exceptions.RequestException as e:
                logger.error(f"Okta API error: {str(e)}")
                return {
                    'success': False,
                    'error': str(e),
                    'users': []
                }

        return {
            'success': True,
            'users': users,
            'count': len(users)
        }

    def _parse_next_link(self, link_header: str) -> str | None:
        """Parse the Link header to extract next page URL"""
        if not link_header:
            return None

        links = link_header.split(',')
        for link in links:
            if 'rel="next"' in link:
                # Extract URL from <URL>; rel="next"
                url = link.split(';')[0].strip().strip('<>')
                return url

        return None

    def get_user_by_email(self, email: str) -> dict | None:
        """
        Get single user by email

        Args:
            email: User email address

        Returns:
            User object or None
        """
        url = f"{self.base_url}/users/{email}"

        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return None
            logger.error(f"Okta API error: {str(e)}")
            raise

    def get_user_by_id(self, user_id: str) -> dict | None:
        """
        Get single user by Okta ID

        Args:
            user_id: Okta user ID

        Returns:
            User object or None
        """
        url = f"{self.base_url}/users/{user_id}"

        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return None
            logger.error(f"Okta API error: {str(e)}")
            raise

    def get_active_users(self) -> dict[str, Any]:
        """Get all active users"""
        return self.get_users(status='ACTIVE')

    def get_deprovisioned_users(self) -> dict[str, Any]:
        """Get all deprovisioned users"""
        return self.get_users(status='DEPROVISIONED')

    def get_suspended_users(self) -> dict[str, Any]:
        """Get all suspended users"""
        return self.get_users(status='SUSPENDED')

    def get_user_groups(self, user_id: str) -> dict[str, Any]:
        """
        Get groups for a specific user

        Args:
            user_id: Okta user ID

        Returns:
            Dict with groups list
        """
        url = f"{self.base_url}/users/{user_id}/groups"

        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            groups = response.json()

            return {
                'success': True,
                'groups': groups,
                'count': len(groups)
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Okta API error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'groups': []
            }

    def transform_user_data(self, okta_user: dict) -> dict[str, Any]:
        """
        Transform Okta user data to our database schema

        Args:
            okta_user: Raw Okta user object

        Returns:
            Transformed user data for database
        """
        profile = okta_user.get('profile', {})

        return {
            'okta_id': okta_user['id'],
            'email': profile.get('email'),
            'first_name': profile.get('firstName'),
            'last_name': profile.get('lastName'),
            'status': okta_user.get('status'),
            'login': profile.get('login'),
            'activated': self._parse_datetime(okta_user.get('activated')),
            'status_changed': self._parse_datetime(okta_user.get('statusChanged')),
            'last_login': self._parse_datetime(okta_user.get('lastLogin')),
            'last_updated': self._parse_datetime(okta_user.get('lastUpdated')),
            'password_changed': self._parse_datetime(okta_user.get('passwordChanged')),
            'department': profile.get('department'),
            'title': profile.get('title'),
            'employee_number': profile.get('employeeNumber'),
            'manager': profile.get('manager'),
            'manager_id': profile.get('managerId'),
            'okta_groups': []  # Will be populated separately if needed
        }

    def _parse_datetime(self, date_string: str | None) -> datetime | None:
        """Parse ISO 8601 datetime string"""
        if not date_string:
            return None

        try:
            # Okta uses ISO 8601 format: 2023-01-15T10:30:45.000Z
            return datetime.fromisoformat(date_string.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            logger.warning(f"Failed to parse datetime: {date_string}")
            return None

    def fetch_all_users_with_groups(self) -> dict[str, Any]:
        """
        Fetch all users from Okta with their group memberships

        Returns:
            Dict with users list (including groups) and metadata
        """
        # First, get all users
        result = self.get_users()

        if not result['success']:
            return result

        users_with_groups = []
        users = result['users']

        for okta_user in users:
            # Transform user data
            user_data = self.transform_user_data(okta_user)

            # Fetch user groups
            groups_result = self.get_user_groups(okta_user['id'])
            if groups_result['success']:
                user_data['okta_groups'] = [
                    {
                        'id': g['id'],
                        'name': g['profile']['name']
                    }
                    for g in groups_result['groups']
                ]

            users_with_groups.append(user_data)

        logger.info(f"Fetched {len(users_with_groups)} users with group memberships")

        return {
            'success': True,
            'users': users_with_groups,
            'count': len(users_with_groups)
        }

    def test_connection(self) -> dict[str, Any]:
        """
        Test Okta API connection

        Returns:
            Dict with connection status
        """
        url = f"{self.base_url}/users"
        params = {'limit': 1}

        try:
            response = requests.get(
                url,
                headers=self.headers,
                params=params,
                timeout=10
            )
            response.raise_for_status()

            return {
                'success': True,
                'message': 'Okta API connection successful',
                'domain': self.domain
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Okta API connection failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'domain': self.domain
            }


def create_okta_client() -> OktaClient:
    """
    Factory function to create Okta client from environment

    Returns:
        OktaClient instance
    """
    return OktaClient()
