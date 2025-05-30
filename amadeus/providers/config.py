import os
import json
import base64
from typing import Dict, Any, Optional, List
import hashlib
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class ProviderConfigManager:
    """
    Gestionnaire pour stocker et récupérer les configurations de provider.
    Gère le stockage sécurisé des informations d'authentification.
    """
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialise le gestionnaire de configuration.
        
        Args:
            config_dir: Répertoire où sont stockées les configurations
        """
        self.config_dir = config_dir or os.path.expanduser("~/.amadeus")
        self.config_file = os.path.join(self.config_dir, "provider_config.secure")
        self._ensure_config_dir()
        
        # Une clé simple basée sur l'utilisateur, à améliorer pour la production
        self.key = self._derive_key()
        self.cipher = Fernet(self.key)
        self._config_cache = None
        
    def _ensure_config_dir(self):
        """S'assure que le répertoire de configuration existe."""
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir, exist_ok=True)
    
    def _derive_key(self) -> bytes:
        """
        Dérive une clé de chiffrement basée sur l'identité de l'utilisateur.
        Note: Pour une version de production, utilisez une méthode plus sécurisée.
        """
        # Utiliser un sel fixe par application et le nom d'utilisateur comme secret
        salt = b"AmadeusConfigManager"
        username = os.environ.get("USER") or os.environ.get("USERNAME") or "default_user"
        password = username.encode() + b"amadeus_salt_pepper"
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))
        return key
    
    def _load_encrypted_config(self) -> Dict[str, Any]:
        """Charge la configuration chiffrée depuis le fichier."""
        if self._config_cache is not None:
            return self._config_cache
        
        if not os.path.exists(self.config_file):
            return {}
        
        try:
            with open(self.config_file, 'rb') as f:
                encrypted_data = f.read()
                if not encrypted_data:
                    return {}
                decrypted_data = self.cipher.decrypt(encrypted_data)
                self._config_cache = json.loads(decrypted_data.decode('utf-8'))
                return self._config_cache
        except Exception as e:
            print(f"Erreur lors du chargement des configurations: {e}")
            return {}
    
    def _save_encrypted_config(self, config: Dict[str, Any]):
        """Enregistre la configuration chiffrée dans le fichier."""
        try:
            self._config_cache = config
            serialized = json.dumps(config).encode('utf-8')
            encrypted_data = self.cipher.encrypt(serialized)
            
            with open(self.config_file, 'wb') as f:
                f.write(encrypted_data)
        except Exception as e:
            print(f"Erreur lors de la sauvegarde des configurations: {e}")
    
    def get_provider_config(self, provider_id: str) -> Dict[str, Any]:
        """
        Récupère la configuration d'un provider spécifique.
        
        Args:
            provider_id: Identifiant du provider
            
        Returns:
            Configuration du provider ou dictionnaire vide si non trouvée
        """
        config = self._load_encrypted_config()
        return config.get(provider_id, {})
    
    def get_all_providers(self) -> List[str]:
        """
        Récupère la liste de tous les providers configurés.
        
        Returns:
            Liste des identifiants des providers configurés
        """
        config = self._load_encrypted_config()
        return list(config.keys())
    
    def get_all_providers_dict(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all providers with their configurations as a dictionary.
        This method provides compatibility with the registry interface.
        
        Returns:
            Dictionary mapping provider_id to config dict
        """
        config = self._load_encrypted_config()
        result = {}
        for provider_id, credentials in config.items():
            result[provider_id] = {
                "credentials": credentials,
                "is_configured": True,
                "is_available": True  # Assume available if configured in file-based system
            }
        return result
    
    def save_provider_config(self, provider_id: str, credentials: Dict[str, str]):
        """
        Sauvegarde la configuration d'un provider.
        
        Args:
            provider_id: Identifiant du provider
            credentials: Dictionnaire des informations d'identification
        """
        config = self._load_encrypted_config()
        config[provider_id] = credentials
        self._save_encrypted_config(config)
    
    def delete_provider_config(self, provider_id: str) -> bool:
        """
        Supprime la configuration d'un provider.
        
        Args:
            provider_id: Identifiant du provider
            
        Returns:
            True si la suppression a réussi
        """
        config = self._load_encrypted_config()
        if provider_id in config:
            del config[provider_id]
            self._save_encrypted_config(config)
            return True
        return False
    
    def check_provider_configured(self, provider_id: str) -> bool:
        """
        Vérifie si un provider est configuré.
        
        Args:
            provider_id: Identifiant du provider
            
        Returns:
            True si le provider est configuré
        """
        config = self._load_encrypted_config()
        return provider_id in config and bool(config[provider_id])
    
    def ensure_provider_exists(self, provider_id: str, name: str, provider_type: str):
        """
        S'assure qu'un provider existe (pour compatibilité avec DBProviderConfigManager).
        Dans le cas du fichier, cette méthode ne fait rien car les providers
        sont créés à la volée lors de la sauvegarde.
        
        Args:
            provider_id: Identifiant du provider
            name: Nom du provider
            provider_type: Type du provider
        """
        # Pour le système de fichiers, pas besoin de pré-créer les providers
        pass
    
    def has_any_providers(self) -> bool:
        """
        Vérifie s'il y a des providers configurés.
        
        Returns:
            True s'il y a au moins un provider configuré
        """
        config = self._load_encrypted_config()
        return len(config) > 0
    
    def get_available_providers(self) -> List[str]:
        """
        Get a list of providers that are both configured and available.
        For file-based system, same as get_all_providers.
        """
        return self.get_all_providers()
