"""
Database-backed provider configuration manager for Amadeus application.
Provides secure storage and retrieval of provider credentials in the database.
"""
import os
import base64
import logging
from typing import Dict, Any, Optional, List
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from sqlalchemy.orm import Session

from ..database.session import get_session
from ..database.models import Provider, ProviderCredential

logger = logging.getLogger(__name__)

class DBProviderConfigManager:
    """
    Database-backed manager for storing and retrieving provider configurations.
    Uses encryption for securely storing authentication credentials in the database.
    """
    
    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize the DB-backed configuration manager.
        
        Args:
            encryption_key: Optional encryption key override (for testing)
        """
        self._config_cache = {}
        self.key = encryption_key.encode() if encryption_key else self._derive_key()
        self.cipher = Fernet(self.key)
        
    def _derive_key(self) -> bytes:
        """
        Derive an encryption key based on the user's identity and environment.
        Uses PBKDF2 for more secure key derivation.
        
        Returns:
            Base64 encoded encryption key
        """
        # Use a fixed salt for the application
        salt = b"AmadeusDBConfigManager"
        
        # Use a combination of environment factors for the password
        # This creates a consistent yet reasonably secure encryption key
        # that doesn't require the user to remember a password
        username = os.environ.get("USER") or os.environ.get("USERNAME") or "default_user"
        machine_id = self._get_machine_id()
        password = (username + "_" + machine_id).encode() + b"amadeus_secure_pepper"
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=150000,  # Increased iterations for better security
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))
        return key
    
    def _get_machine_id(self) -> str:
        """
        Get a unique identifier for the current machine.
        Falls back to username if no machine ID can be determined.
        
        Returns:
            String identifier for the machine
        """
        # Try to get a machine-specific identifier
        # This will be more stable than just using the username
        machine_id = "unknown"
        
        # Try reading machine-id from systemd
        try:
            if os.path.exists("/etc/machine-id"):
                with open("/etc/machine-id", "r") as f:
                    machine_id = f.read().strip()
                    return machine_id
        except Exception:
            pass
            
        # Try reading from dbus machine ID on Linux/Unix systems
        try:
            if os.path.exists("/var/lib/dbus/machine-id"):
                with open("/var/lib/dbus/machine-id", "r") as f:
                    machine_id = f.read().strip()
                    return machine_id
        except Exception:
            pass
            
        # On Windows, try using the registry
        try:
            if os.name == "nt":
                import winreg
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                                    r"SOFTWARE\Microsoft\Cryptography") as key:
                    machine_id, _ = winreg.QueryValueEx(key, "MachineGuid")
                    return machine_id
        except Exception:
            pass
            
        # Fall back to username plus hostname
        try:
            import socket
            username = os.environ.get("USER") or os.environ.get("USERNAME") or "default_user"
            hostname = socket.gethostname()
            return f"{username}_{hostname}"
        except Exception:
            pass
        
        return machine_id
    
    def _encrypt_value(self, value: str) -> str:
        """
        Encrypt a value using the encryption key.
        
        Args:
            value: String value to encrypt
            
        Returns:
            Base64 encoded encrypted value
        """
        encrypted = self.cipher.encrypt(value.encode('utf-8'))
        return encrypted.decode('utf-8')
    
    def _decrypt_value(self, encrypted_value: str) -> str:
        """
        Decrypt an encrypted value.
        
        Args:
            encrypted_value: Base64 encoded encrypted value
            
        Returns:
            Decrypted string value
        """
        try:
            decrypted = self.cipher.decrypt(encrypted_value.encode('utf-8'))
            return decrypted.decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to decrypt value: {e}")
            return ""
    
    def get_provider_config(self, provider_id: str) -> Dict[str, Any]:
        """
        Retrieve configuration for a specific provider from the database.
        
        Args:
            provider_id: Identifier of the provider
            
        Returns:
            Provider configuration dictionary or empty dict if not found
        """
        # Check cache first
        if provider_id in self._config_cache:
            return self._config_cache[provider_id].copy()
        
        result = {}
        session = get_session()
        
        try:
            provider = self._find_provider(session, provider_id)
            if not provider:
                return {}
                
            # Get all credentials for this provider
            for cred in provider.credentials:
                try:
                    decrypted_value = self._decrypt_value(cred.encrypted_value)
                    result[cred.key] = decrypted_value
                except Exception as e:
                    logger.error(f"Error decrypting credential {cred.key} for provider {provider_id}: {e}")
            
            # Cache the result
            self._config_cache[provider_id] = result.copy()
            return result
        
        except Exception as e:
            logger.error(f"Error retrieving provider config for {provider_id}: {e}")
            return {}
        finally:
            session.close()
    
    def get_all_providers(self) -> List[str]:
        """
        Get a list of all configured providers.
        
        Returns:
            List of provider IDs
        """
        session = get_session()
        try:
            providers = session.query(Provider).all()
            return [p.provider_id for p in providers]
        except Exception as e:
            logger.error(f"Error retrieving all providers: {e}")
            return []
        finally:
            session.close()
    
    def get_available_providers(self) -> List[str]:
        """
        Get a list of providers that are both configured and available.
        
        Returns:
            List of available provider IDs
        """
        session = get_session()
        try:
            providers = session.query(Provider).filter(
                Provider.is_configured == True,
                Provider.is_available == True
            ).all()
            return [p.provider_id for p in providers]
        except Exception as e:
            logger.error(f"Error retrieving available providers: {e}")
            return []
        finally:
            session.close()
    
    def save_provider_config(self, provider_id: str, credentials: Dict[str, str]):
        """
        Save provider configuration to the database.
        
        Args:
            provider_id: Identifier of the provider
            credentials: Dictionary of credential key-value pairs
        """
        session = get_session()
        
        try:
            # Find or create provider
            provider = self._find_provider(session, provider_id)
            if not provider:
                # Create new provider record
                provider = Provider(
                    provider_id=provider_id,
                    name=provider_id.capitalize(),  # Default name, can be updated later
                    provider_type=self._guess_provider_type(provider_id),
                    is_configured=True
                )
                session.add(provider)
                session.flush()  # Generate ID for the new provider
            
            # Clear existing credentials
            for cred in provider.credentials:
                session.delete(cred)
            
            # Store new credentials
            for key, value in credentials.items():
                encrypted_value = self._encrypt_value(value)
                cred = ProviderCredential(
                    provider_id=provider.id,
                    key=key,
                    encrypted_value=encrypted_value
                )
                session.add(cred)
            
            # Update provider status
            provider.is_configured = True
            
            session.commit()
            
            # Update cache
            self._config_cache[provider_id] = credentials.copy()
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving provider config for {provider_id}: {e}")
            raise
        finally:
            session.close()
    
    def _find_provider(self, session: Session, provider_id: str) -> Optional[Provider]:
        """
        Find a provider in the database by ID.
        
        Args:
            session: Database session
            provider_id: Provider identifier
            
        Returns:
            Provider object or None if not found
        """
        return session.query(Provider).filter(Provider.provider_id == provider_id).first()
    
    def _guess_provider_type(self, provider_id: str) -> str:
        """
        Make an educated guess about the provider type based on its ID.
        
        Args:
            provider_id: Provider identifier
            
        Returns:
            Provider type ("cloud" or "local")
        """
        # List of known cloud providers
        cloud_providers = [
            "openai", "anthropic", "google", "cohere", "azure", "mistral", 
            "huggingface", "ai_studio", "claude", "gemini"
        ]
        
        # List of known local providers
        local_providers = ["ollama", "llama.cpp", "unsloth", "mlx", "pytorch"]
        
        # Check if provider_id contains or matches any known provider names
        for cloud in cloud_providers:
            if cloud in provider_id.lower():
                return "cloud"
                
        for local in local_providers:
            if local in provider_id.lower():
                return "local"
        
        # Default to cloud if unknown
        return "cloud"
    
    def delete_provider_config(self, provider_id: str) -> bool:
        """
        Delete a provider configuration from the database.
        
        Args:
            provider_id: Identifier of the provider
            
        Returns:
            True if the provider was found and deleted, False otherwise
        """
        session = get_session()
        try:
            provider = self._find_provider(session, provider_id)
            if not provider:
                return False
            
            # Delete all related credentials
            for cred in provider.credentials:
                session.delete(cred)
            
            # Update provider status rather than deleting the record
            provider.is_configured = False
            session.commit()
            
            # Remove from cache
            if provider_id in self._config_cache:
                del self._config_cache[provider_id]
                
            return True
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error deleting provider config for {provider_id}: {e}")
            return False
        finally:
            session.close()
    
    def check_provider_configured(self, provider_id: str) -> bool:
        """
        Check if a provider is configured in the database.
        
        Args:
            provider_id: Identifier of the provider
            
        Returns:
            True if the provider is configured, False otherwise
        """
        session = get_session()
        try:
            provider = self._find_provider(session, provider_id)
            if not provider:
                return False
                
            return provider.is_configured and len(provider.credentials) > 0
            
        except Exception as e:
            logger.error(f"Error checking provider configuration for {provider_id}: {e}")
            return False
        finally:
            session.close()
    
    def update_provider_availability(self, provider_id: str, is_available: bool):
        """
        Update the availability status of a provider.
        
        Args:
            provider_id: Identifier of the provider
            is_available: Whether the provider is available
        """
        session = get_session()
        try:
            provider = self._find_provider(session, provider_id)
            if provider:
                provider.is_available = is_available
                provider.last_check_time = session.now()
                session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating provider availability for {provider_id}: {e}")
        finally:
            session.close()
    
    def update_provider_metadata(self, provider_id: str, name: str = None, provider_type: str = None):
        """
        Update metadata for a provider.
        
        Args:
            provider_id: Identifier of the provider
            name: Display name for the provider
            provider_type: Type of provider ("cloud" or "local")
        """
        session = get_session()
        try:
            provider = self._find_provider(session, provider_id)
            if provider:
                if name:
                    provider.name = name
                if provider_type:
                    provider.provider_type = provider_type
                session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating provider metadata for {provider_id}: {e}")
        finally:
            session.close()
