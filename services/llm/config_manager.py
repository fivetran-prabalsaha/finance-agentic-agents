"""
LLM Configuration Manager

Handles configuration loading, encryption, and decryption of API keys
"""

import json
import logging
import os
from typing import Any

import yaml
from cryptography.fernet import Fernet

from .base import LLMConfig
from .factory import LLMProviderFactory

logger = logging.getLogger(__name__)


class ConfigEncryption:
    """Handles encryption/decryption of sensitive configuration data"""

    def __init__(self, master_key: str | None = None):
        """
        Initialize encryption handler

        Args:
            master_key: Master encryption key (base64 encoded Fernet key)
                       If not provided, reads from MASTER_ENCRYPTION_KEY env var
        """
        self.master_key = master_key or os.getenv('MASTER_ENCRYPTION_KEY')

        if not self.master_key:
            logger.warning(
                "No MASTER_ENCRYPTION_KEY found. Encryption disabled. "
                "Generate one with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            )
            self.cipher = None
        else:
            try:
                self.cipher = Fernet(self.master_key.encode())
            except Exception as e:
                logger.error(f"Invalid master key: {str(e)}")
                self.cipher = None

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext

        Args:
            plaintext: Text to encrypt

        Returns:
            Encrypted text (base64 encoded)
        """
        if not self.cipher:
            logger.warning("Encryption not configured. Returning plaintext.")
            return plaintext

        try:
            encrypted = self.cipher.encrypt(plaintext.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error(f"Encryption failed: {str(e)}")
            return plaintext

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt ciphertext

        Args:
            ciphertext: Encrypted text (base64 encoded)

        Returns:
            Decrypted plaintext
        """
        if not self.cipher:
            # If encryption not configured, assume plaintext
            return ciphertext

        try:
            decrypted = self.cipher.decrypt(ciphertext.encode())
            return decrypted.decode()
        except Exception as e:
            # If decryption fails, might be plaintext
            logger.warning(f"Decryption failed, assuming plaintext: {str(e)}")
            return ciphertext

    @staticmethod
    def generate_key() -> str:
        """
        Generate a new Fernet encryption key

        Returns:
            Base64 encoded key
        """
        return Fernet.generate_key().decode()


class LLMConfigManager:
    """
    Manages LLM configuration from files and environment variables

    Supports:
    - YAML/JSON config files
    - Encrypted API keys
    - Environment variable fallback
    - Multiple provider configurations
    """

    def __init__(
        self,
        config_path: str | None = None,
        master_key: str | None = None
    ):
        """
        Initialize config manager

        Args:
            config_path: Path to config file (YAML or JSON)
            master_key: Master encryption key
        """
        self.config_path = config_path or os.getenv(
            'LLM_CONFIG_PATH',
            'config/llm_config.yaml'
        )

        self.encryption = ConfigEncryption(master_key)
        self.config_data: dict[str, Any] = {}

        if os.path.exists(self.config_path):
            self.load_config()
        else:
            logger.warning(f"Config file not found: {self.config_path}")

    def load_config(self) -> None:
        """Load configuration from file"""
        try:
            with open(self.config_path) as f:
                if self.config_path.endswith('.yaml') or self.config_path.endswith('.yml'):
                    self.config_data = yaml.safe_load(f)
                elif self.config_path.endswith('.json'):
                    self.config_data = json.load(f)
                else:
                    raise ValueError(f"Unsupported config file format: {self.config_path}")

            logger.info(f"Loaded LLM config from {self.config_path}")

        except Exception as e:
            logger.error(f"Failed to load config: {str(e)}")
            raise

    def save_config(self, config_path: str | None = None) -> None:
        """
        Save configuration to file

        Args:
            config_path: Path to save config (defaults to loaded path)
        """
        save_path = config_path or self.config_path

        try:
            with open(save_path, 'w') as f:
                if save_path.endswith('.yaml') or save_path.endswith('.yml'):
                    yaml.dump(self.config_data, f, default_flow_style=False)
                elif save_path.endswith('.json'):
                    json.dump(self.config_data, f, indent=2)

            logger.info(f"Saved LLM config to {save_path}")

        except Exception as e:
            logger.error(f"Failed to save config: {str(e)}")
            raise

    def get_provider_config(self, provider_name: str | None = None) -> LLMConfig:
        """
        Get LLM configuration for a specific provider

        Args:
            provider_name: Provider name (uses default if not specified)

        Returns:
            LLM configuration

        Raises:
            ValueError: If provider not found or config invalid
        """
        # Determine which provider to use
        if not provider_name:
            provider_name = self.config_data.get('default_provider')

        if not provider_name:
            raise ValueError("No provider specified and no default_provider in config")

        # Get provider config
        providers = self.config_data.get('providers', {})
        provider_config = providers.get(provider_name)

        if not provider_config:
            raise ValueError(f"Provider '{provider_name}' not found in config")

        # Get API key (try config, then environment, then decrypt if encrypted)
        api_key = provider_config.get('api_key')

        if not api_key:
            # Try environment variable
            env_var = provider_config.get('api_key_env')
            if env_var:
                api_key = os.getenv(env_var)

        if not api_key:
            raise ValueError(f"No API key found for provider '{provider_name}'")

        # Decrypt API key if encrypted
        if provider_config.get('encrypted', False):
            api_key = self.encryption.decrypt(api_key)

        # Build LLMConfig
        return LLMConfig(
            provider=provider_name,
            model=provider_config['model'],
            api_key=api_key,
            api_base=provider_config.get('api_base'),
            temperature=provider_config.get('temperature', 0.0),
            max_tokens=provider_config.get('max_tokens', 4096),
            timeout=provider_config.get('timeout', 120),
            max_retries=provider_config.get('max_retries', 3),
            streaming=provider_config.get('streaming', False),
            extra_params=provider_config.get('extra_params')
        )

    def get_llm_provider(self, provider_name: str | None = None):
        """
        Get instantiated LLM provider

        Args:
            provider_name: Provider name (uses default if not specified)

        Returns:
            Instantiated LLM provider
        """
        config = self.get_provider_config(provider_name)
        return LLMProviderFactory.create_provider(config)

    def encrypt_api_key(self, api_key: str) -> str:
        """
        Encrypt an API key

        Args:
            api_key: Plaintext API key

        Returns:
            Encrypted API key
        """
        return self.encryption.encrypt(api_key)

    def set_provider_config(
        self,
        provider_name: str,
        model: str,
        api_key: str,
        encrypt_key: bool = True,
        **kwargs
    ) -> None:
        """
        Add or update provider configuration

        Args:
            provider_name: Provider name
            model: Model name
            api_key: API key
            encrypt_key: Whether to encrypt the API key
            **kwargs: Additional configuration parameters
        """
        if 'providers' not in self.config_data:
            self.config_data['providers'] = {}

        # Encrypt API key if requested
        if encrypt_key:
            api_key = self.encrypt_api_key(api_key)

        self.config_data['providers'][provider_name] = {
            'model': model,
            'api_key': api_key,
            'encrypted': encrypt_key,
            **kwargs
        }

        logger.info(f"Set configuration for provider '{provider_name}'")

    def list_providers(self) -> list:
        """
        List all configured providers

        Returns:
            List of provider names
        """
        return list(self.config_data.get('providers', {}).keys())

    def set_default_provider(self, provider_name: str) -> None:
        """
        Set default provider

        Args:
            provider_name: Provider name to set as default
        """
        if provider_name not in self.config_data.get('providers', {}):
            raise ValueError(f"Provider '{provider_name}' not found in config")

        self.config_data['default_provider'] = provider_name
        logger.info(f"Set default provider to '{provider_name}'")

    def get_default_provider(self) -> str | None:
        """
        Get default provider name

        Returns:
            Default provider name or None
        """
        return self.config_data.get('default_provider')


# Convenience function
def get_llm_from_config(
    config_path: str | None = None,
    provider: str | None = None
):
    """
    Convenience function to get LLM provider from config file

    Args:
        config_path: Path to config file
        provider: Provider name (uses default if not specified)

    Returns:
        Instantiated LLM provider

    Example:
        >>> llm = get_llm_from_config(
        ...     config_path="config/llm_config.yaml",
        ...     provider="anthropic"
        ... )
        >>> response = llm.generate([
        ...     LLMMessage(role="user", content="Hello!")
        ... ])
    """
    manager = LLMConfigManager(config_path)
    return manager.get_llm_provider(provider)
