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
        CROSS-PLATFORM: Works on Windows, macOS, and Linux without external dependencies.
        
        Returns:
            String identifier for the machine
        """
        # Try to get a machine-specific identifier
        # This will be more stable than just using the username
        machine_id = "unknown"
        
        # Linux/Unix: Try reading machine-id from systemd (most modern Linux distributions)
        try:
            if os.path.exists("/etc/machine-id"):
                with open("/etc/machine-id", "r") as f:
                    machine_id = f.read().strip()
                    return machine_id
        except Exception:
            pass
            
        # Linux/Unix: Try reading from dbus machine ID (fallback for older systems)
        try:
            if os.path.exists("/var/lib/dbus/machine-id"):
                with open("/var/lib/dbus/machine-id", "r") as f:
                    machine_id = f.read().strip()
                    return machine_id
        except Exception:
            pass
            
        # Windows: Use the registry to get MachineGuid (no external tools needed)
        try:
            if os.name == "nt":
                import winreg  # Built into Python on Windows
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                                    r"SOFTWARE\Microsoft\Cryptography") as key:
                    machine_id, _ = winreg.QueryValueEx(key, "MachineGuid")
                    return machine_id
        except Exception:
            pass
            
        # Universal fallback: username + hostname (works on all OS)
        try:
            import socket  # Built into Python standard library
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
    
    def get_all_providers_dict(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all providers with their configurations as a dictionary.
        This method provides compatibility with the registry interface.
        
        Returns:
            Dictionary mapping provider_id to config dict
        """
        session = get_session()
        try:
            providers = session.query(Provider).all()
            result = {}
            for provider in providers:
                result[provider.provider_id] = {
                    "name": provider.name,
                    "provider_type": provider.provider_type,
                    "is_configured": provider.is_configured,
                    "is_available": provider.is_available
                }
            return result
        except Exception as e:
            logger.error(f"Error retrieving all providers dict: {e}")
            return {}
        finally:
            session.close()
    
    def has_any_providers(self) -> bool:
        """
        Check if any providers are configured.
        
        Returns:
            True if at least one provider is configured
        """
        session = get_session()
        try:
            count = session.query(Provider).filter(Provider.is_configured == True).count()
            return count > 0
        except Exception as e:
            logger.error(f"Error checking for configured providers: {e}")
            return False
        finally:
            session.close()
    
    def _find_provider(self, session: Session, provider_id: str) -> Optional[Any]:
        """
        Find a provider in the database by ID.
        
        Args:
            session: Database session
            provider_id: Provider identifier
            
        Returns:
            Provider instance or None
        """
        try:
            return session.query(Provider).filter_by(provider_id=provider_id).first()
        except Exception as e:
            logger.error(f"Error finding provider {provider_id}: {e}")
            return None
    
    def save_provider_config(self, provider_id: str, credentials: Dict[str, str]):
        """
        Save provider configuration to the database.
        
        Args:
            provider_id: Provider identifier
            credentials: Dictionary of credentials to save
        """
        session = get_session()
        try:
            # Find or create provider
            provider = self._find_provider(session, provider_id)
            if not provider:
                logger.error(f"Provider {provider_id} not found in database. Cannot save credentials.")
                raise ValueError(f"Provider {provider_id} must exist before saving credentials")
            
            # Remove existing credentials
            session.query(ProviderCredential).filter_by(provider_id=provider.id).delete()
            
            # Add new credentials
            for key, value in credentials.items():
                if value:  # Only save non-empty values
                    encrypted_value = self._encrypt_value(str(value))
                    credential = ProviderCredential(
                        provider_id=provider.id,
                        key=key,
                        encrypted_value=encrypted_value
                    )
                    session.add(credential)
            
            # Mark provider as configured
            provider.is_configured = True
            session.commit()
            
            # Clear cache
            if provider_id in self._config_cache:
                del self._config_cache[provider_id]
            
            logger.info(f"Saved configuration for provider {provider_id}")
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving provider config for {provider_id}: {e}")
            raise
        finally:
            session.close()
    
    def delete_provider_config(self, provider_id: str) -> bool:
        """
        Delete provider configuration from the database.
        
        Args:
            provider_id: Provider identifier
            
        Returns:
            True if deletion was successful
        """
        session = get_session()
        try:
            provider = self._find_provider(session, provider_id)
            if not provider:
                logger.warning(f"Provider {provider_id} not found for deletion")
                return False
            
            # Delete all credentials
            deleted_count = session.query(ProviderCredential).filter_by(provider_id=provider.id).delete()
            
            # Mark provider as not configured
            provider.is_configured = False
            session.commit()
            
            # Clear cache
            if provider_id in self._config_cache:
                del self._config_cache[provider_id]
            
            logger.info(f"Deleted {deleted_count} credentials for provider {provider_id}")
            return True
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error deleting provider config for {provider_id}: {e}")
            return False
        finally:
            session.close()
    
    def check_provider_configured(self, provider_id: str) -> bool:
        """
        Check if a provider is configured.
        
        Args:
            provider_id: Provider identifier
            
        Returns:
            True if provider is configured
        """
        session = get_session()
        try:
            provider = self._find_provider(session, provider_id)
            return provider and provider.is_configured
        except Exception as e:
            logger.error(f"Error checking if provider {provider_id} is configured: {e}")
            return False
        finally:
            session.close()
    
    def ensure_provider_exists(self, provider_id: str, name: str, provider_type: str):
        """
        Ensure a provider exists in the database.
        
        Args:
            provider_id: Provider identifier
            name: Provider name
            provider_type: Provider type (cloud/local)
        """
        session = get_session()
        try:
            provider = self._find_provider(session, provider_id)
            if not provider:
                provider = Provider(
                    provider_id=provider_id,
                    name=name,
                    provider_type=provider_type,
                    is_available=True,
                    is_configured=False
                )
                session.add(provider)
                session.commit()
                logger.info(f"Created new provider entry: {provider_id}")
            else:
                # Update name and type if they've changed
                if provider.name != name or provider.provider_type != provider_type:
                    provider.name = name
                    provider.provider_type = provider_type
                    session.commit()
                    logger.debug(f"Updated provider info: {provider_id}")
                    
        except Exception as e:
            session.rollback()
            logger.error(f"Error ensuring provider exists {provider_id}: {e}")
            raise
        finally:
            session.close()
