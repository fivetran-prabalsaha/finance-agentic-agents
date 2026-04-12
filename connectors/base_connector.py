"""
Base Connector - Abstract base class for all system connectors
"""
import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class BaseConnector(ABC):
    """
    Abstract base class for external system connectors

    All connectors (NetSuite, Okta, Salesforce, etc.) must implement
    this interface for consistent behavior across the system.
    """

    def __init__(self, system_name: str):
        """
        Initialize connector

        Args:
            system_name: Name of the system (e.g., 'netsuite', 'okta')
        """
        self.system_name = system_name
        logger.info(f"Initialized {system_name} connector")

    @abstractmethod
    def test_connection_sync(self) -> bool:
        """
        Test connection to external system

        Returns:
            True if connection successful, False otherwise
        """
        pass

    @abstractmethod
    def get_user_count_sync(self) -> int:
        """
        Get total number of users in the system

        Returns:
            Number of users
        """
        pass

    @abstractmethod
    def fetch_users_with_roles_sync(self, **kwargs) -> list[dict[str, Any]]:
        """
        Fetch all users with their roles from external system

        Args:
            **kwargs: System-specific parameters

        Returns:
            List of user dictionaries with roles
        """
        pass

    @abstractmethod
    def sync_to_database_sync(
        self,
        users_data: list[dict[str, Any]],
        user_repo,
        role_repo
    ) -> list[Any]:
        """
        Sync fetched users to local database

        Args:
            users_data: List of user dictionaries from external system
            user_repo: UserRepository instance
            role_repo: RoleRepository instance

        Returns:
            List of synced User objects
        """
        pass

    @abstractmethod
    def get_system_type(self) -> str:
        """
        Get system type classification

        Returns:
            System type (e.g., 'ERP', 'Identity', 'CRM')
        """
        pass

    def get_system_name(self) -> str:
        """Get system name"""
        return self.system_name
