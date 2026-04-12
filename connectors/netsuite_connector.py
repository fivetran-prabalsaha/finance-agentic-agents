"""
NetSuite Connector - Wraps existing NetSuite client for MCP integration
"""
import logging
from datetime import datetime
from datetime import datetime as _datetime
from typing import Any

from services.netsuite_client import NetSuiteClient

from .base_connector import BaseConnector

logger = logging.getLogger(__name__)


class NetSuiteConnector(BaseConnector):
    """
    NetSuite connector for MCP integration

    Wraps the existing NetSuiteClient and provides async interface
    compatible with BaseConnector.
    """

    def __init__(self):
        super().__init__("netsuite")
        self.client = NetSuiteClient()
        logger.info("NetSuite connector initialized with existing client")

    def test_connection_sync(self) -> bool:
        """
        Test NetSuite connection

        Returns:
            True if connection successful, False otherwise
        """
        try:
            return self.client.test_connection()
        except Exception as e:
            logger.error(f"NetSuite connection test failed: {str(e)}")
            return False

    def get_user_count_sync(self) -> int:
        """
        Get total number of active users in NetSuite

        Returns:
            Number of active users
        """
        try:
            result = self.client.get_users_and_roles(
                limit=1,
                include_permissions=False
            )

            if result.get('success'):
                return result['data']['metadata'].get('total_users', 0)
            return 0

        except Exception as e:
            logger.error(f"Failed to get NetSuite user count: {str(e)}")
            return 0

    def fetch_users_with_roles_sync(
        self,
        include_permissions: bool = True,
        include_inactive: bool = False,
        last_modified_after: _datetime | None = None,
        **kwargs
    ) -> list[dict[str, Any]]:
        """
        Fetch all users with their roles from NetSuite

        Args:
            include_permissions: Include detailed role permissions
            include_inactive: Include inactive users
            last_modified_after: Only return users modified after this datetime (incremental sync)
            **kwargs: Additional parameters (subsidiary, department, etc.)

        Returns:
            List of user dictionaries with roles
        """
        logger.info(f"Fetching users from NetSuite (permissions={include_permissions}, incremental={last_modified_after is not None})")

        try:
            # Use paginated fetch for all users
            # NetSuite RESTlet limits to 200 users per page max
            result = self.client.get_all_users_paginated(
                include_permissions=include_permissions,
                status='ACTIVE' if not include_inactive else 'ALL',
                page_size=200,
                last_modified_after=last_modified_after
            )

            if not result.get('success'):
                logger.error(f"Failed to fetch users: {result.get('error')}")
                return []

            users = result['data']['users']
            logger.info(f"Fetched {len(users)} users from NetSuite")

            return users

        except Exception as e:
            logger.error(f"Error fetching users from NetSuite: {str(e)}")
            raise

    def search_user_sync(
        self,
        search_value: str,
        search_type: str = 'both',
        include_permissions: bool = True
    ) -> dict[str, Any] | None:
        """
        Search for a specific user in NetSuite

        Args:
            search_value: Name or email to search for
            search_type: 'name', 'email', or 'both'
            include_permissions: Include role permissions

        Returns:
            User dictionary if found, None otherwise
        """
        logger.info(f"Searching NetSuite for user: {search_value}")

        try:
            result = self.client.search_users(
                search_value=search_value,
                search_type=search_type,
                include_permissions=include_permissions
            )

            if result.get('success') and result['data']['users']:
                return result['data']['users'][0]

            return None

        except Exception as e:
            logger.error(f"Error searching NetSuite user: {str(e)}")
            return None

    def sync_to_database_sync(
        self,
        users_data: list[dict[str, Any]],
        user_repo,
        role_repo
    ) -> list[Any]:
        """
        Sync NetSuite users to local database

        Args:
            users_data: List of user dictionaries from NetSuite
            user_repo: UserRepository instance

        Returns:
            List of synced User model objects
        """
        logger.info(f"Syncing {len(users_data)} NetSuite users to database")

        synced_users = []

        try:
            for user_data in users_data:
                # Extract user info
                email = user_data.get('email')
                if not email:
                    logger.warning(f"Skipping user without email: {user_data.get('name')}")
                    continue

                # Extract job title from various possible field names
                # NetSuite might return it as: title, jobTitle, jobtitle, job_title
                job_title = (
                    user_data.get('title') or
                    user_data.get('jobTitle') or
                    user_data.get('jobtitle') or
                    user_data.get('job_title') or
                    user_data.get('jobTitle.name') or  # NetSuite often uses .name for text fields
                    user_data.get('title.name') or
                    None
                )

                # Log if title is missing (for debugging)
                if not job_title:
                    logger.debug(f"No job title found for {email}. Available fields: {list(user_data.keys())}")

                # Upsert user - prepare dictionary for upsert_user
                user_dict = {
                    'user_id': str(user_data.get('user_id', '')),
                    'internal_id': str(user_data.get('internal_id', user_data.get('user_id', ''))),
                    'name': user_data.get('name', ''),
                    'email': email,
                    'status': 'ACTIVE' if user_data.get('is_active', True) else 'INACTIVE',
                    'department': user_data.get('department'),
                    'subsidiary': user_data.get('subsidiary'),
                    'employee_id': user_data.get('employee_id'),
                    'job_function': user_data.get('job_function'),
                    'business_unit': user_data.get('business_unit'),
                    'title': job_title,  # Use extracted job title
                    'location': user_data.get('location'),
                    'supervisor': user_data.get('supervisor'),
                    'supervisor_id': user_data.get('supervisor_id'),
                    'hire_date': user_data.get('hire_date'),
                    'last_login': user_data.get('last_login')
                }
                user = user_repo.upsert_user(user_dict)

                # Sync roles — upsert current roles, then remove stale ones
                roles = user_data.get('roles', [])
                paginated_returned_roles = bool(roles)  # Track before fallback

                # Fallback: if paginated RESTlet returned 0 roles but user has DB roles,
                # verify via search endpoint before wiping.
                # The paginated RESTlet is a finance-role focused saved search — it only
                # returns role data for ~45/1934 users (finance/accounting roles).
                # For all other users (including Admin role holders), roles=[] from paginated
                # is NOT authoritative — must verify via search.
                existing_role_ids_pre = {str(ur.role_id) for ur in user.user_roles}
                if not roles and existing_role_ids_pre:
                    logger.warning(
                        f"Paginated RESTlet returned 0 roles for {email} "
                        f"(has {len(existing_role_ids_pre)} in DB) — verifying via search"
                    )
                    search_result = self.search_user_sync(
                        search_value=email,
                        search_type='email',
                        include_permissions=True
                    )
                    if search_result and search_result.get('roles'):
                        roles = search_result['roles']
                        paginated_returned_roles = True  # Search is authoritative too
                        logger.info(
                            f"Search fallback found {len(roles)} role(s) for {email}: "
                            f"{[r.get('role_name') for r in roles]}"
                        )
                    else:
                        logger.warning(
                            f"Search also returned 0 roles for {email} — proceeding with removal"
                        )

                current_role_ids: set = set()

                for role_data in roles:
                    role_name = role_data.get('role_name')
                    role_id_str = str(role_data.get('role_id', role_name))

                    if not role_name or not role_id_str:
                        continue

                    # Upsert role first
                    role = role_repo.upsert_role({
                        'role_id': role_id_str,
                        'role_name': role_name,
                        'is_custom': role_data.get('is_custom', False),
                        'description': role_data.get('description'),
                        'permission_count': len(role_data.get('permissions', [])),
                        'permissions': role_data.get('permissions', [])
                    })

                    # Assign role to user
                    user_repo.assign_role_to_user(
                        user_id=str(user.id),
                        role_id=str(role.id)
                    )
                    current_role_ids.add(str(role.id))

                # Remove roles that are no longer assigned in NetSuite.
                # Only do this when we have authoritative role data (paginated returned roles,
                # or search fallback confirmed the current set). If neither source returned
                # role data for this user, skip removal to avoid false positives — the
                # paginated RESTlet only covers finance/accounting roles, not all roles.
                if paginated_returned_roles:
                    existing_role_ids = {str(ur.role_id) for ur in user.user_roles}
                    stale_role_ids = existing_role_ids - current_role_ids
                    for stale_id in stale_role_ids:
                        user_repo.remove_role_from_user(str(user.id), stale_id)
                        logger.info(
                            f"Removed stale role {stale_id} from {user_data.get('email', user.id)}"
                        )

                synced_users.append(user)

            logger.info(f"Successfully synced {len(synced_users)} users to database")
            return synced_users

        except Exception as e:
            logger.error(f"Error syncing users to database: {str(e)}")
            raise

    def get_system_type(self) -> str:
        """Get system type"""
        return "ERP"

    def get_last_sync_date_sync(self, violation_repo) -> datetime | None:
        """
        Get the date of the last sync/review

        Args:
            violation_repo: ViolationRepository instance (for compatibility)

        Returns:
            Last sync datetime or None
        """
        try:
            # Use SyncMetadataRepository to get last sync date
            from models.database_config import DatabaseConfig
            from repositories.sync_metadata_repository import SyncMetadataRepository

            db_config = DatabaseConfig()
            session = db_config.get_session()
            sync_repo = SyncMetadataRepository(session)

            last_sync = sync_repo.get_last_successful_sync('netsuite')

            if last_sync and last_sync.completed_at:
                return last_sync.completed_at

            # Fallback: check for recent violations if no sync record
            try:
                open_violations = violation_repo.get_open_violations(limit=1)
                if open_violations:
                    return open_violations[0].detected_at
            except Exception:
                pass

            return None

        except Exception as e:
            logger.error(f"Error getting last sync date: {str(e)}")
            return None
