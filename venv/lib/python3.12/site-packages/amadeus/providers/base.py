from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import json
import os
import logging

class Provider(ABC):
    """
    Classe abstraite de base pour tous les providers.
    Chaque provider doit implémenter cette interface.
    """
    
    def __init__(self, provider_id: str, config_path: Optional[str] = None):
        """
        Initialise un provider avec son identifiant et son chemin de configuration.
        
        Args:
            provider_id: Identifiant unique du provider
            config_path: Chemin vers le fichier de configuration (config.json)
        """
        self.provider_id = provider_id
        self.config_path = config_path or self._get_default_config_path()
        self.logger = logging.getLogger(f"amadeus.providers.{provider_id}")
        
        # Chargement de la configuration
        self.config = self._load_config()
        self.is_available = True
        
        # Synchronisation avec la base de données
        self._sync_with_database()
        
    def _sync_with_database(self):
        """Synchronise l'état du provider avec la base de données."""
        try:
            # Import à l'intérieur de la méthode pour éviter les dépendances circulaires
            from ..database.session import get_session
            from ..database.models import Provider as DBProvider
            
            session = get_session()
            try:
                # Vérifier si le provider existe dans la base de données
                db_provider = session.query(DBProvider).filter(DBProvider.provider_id == self.provider_id).first()
                
                if db_provider:
                    # Mettre à jour l'état de disponibilité
                    self.is_available = db_provider.is_available
                    
                    # Mise à jour des informations du provider si nécessaire
                    if db_provider.name != self.name or db_provider.provider_type != self.type:
                        db_provider.name = self.name
                        db_provider.provider_type = self.type
                        session.commit()
                else:
                    # Créer une entrée dans la DB pour ce provider
                    db_provider = DBProvider(
                        provider_id=self.provider_id,
                        name=self.name,
                        provider_type=self.type,
                        is_available=True
                    )
                    session.add(db_provider)
                    session.commit()
                    
                self.logger.debug(f"Provider {self.provider_id} synchronisé avec la base de données")
                
            finally:
                session.close()
                
        except Exception as e:
            self.logger.error(f"Erreur lors de la synchronisation avec la base de données: {e}")
            self.logger.debug("Détails:", exc_info=True)
        
    def _get_default_config_path(self) -> str:
        """Obtient le chemin par défaut du fichier de configuration."""
        module_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Déterminer le type (local/cloud) à partir de la structure du package
        if "local" in self.__module__:
            provider_type = "local"
        else:
            provider_type = "cloud"
            
        # Extraire le nom du provider à partir du nom du module
        provider_name = self.__module__.split('.')[-2]
        
        return os.path.join(module_dir, provider_type, provider_name, "config.json")
    
    def _load_config(self) -> Dict[str, Any]:
        """Charge la configuration du provider depuis le fichier config.json."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.logger.debug(f"Configuration chargée pour {self.provider_id}")
                return config
        except FileNotFoundError:
            error_msg = f"Configuration non trouvée pour le provider {self.provider_id}"
            self.logger.error(error_msg)
            self.is_available = False
            self._update_availability_in_db(False)
            raise FileNotFoundError(error_msg)
        except json.JSONDecodeError:
            error_msg = f"Format de configuration invalide pour le provider {self.provider_id}"
            self.logger.error(error_msg)
            self.is_available = False
            self._update_availability_in_db(False)
            raise ValueError(error_msg)
    
    def _update_availability_in_db(self, is_available: bool):
        """Met à jour l'état de disponibilité dans la base de données."""
        try:
            from ..database.session import get_session
            from ..database.models import Provider as DBProvider
            
            session = get_session()
            try:
                db_provider = session.query(DBProvider).filter(DBProvider.provider_id == self.provider_id).first()
                
                if db_provider:
                    db_provider.is_available = is_available
                    session.commit()
                    self.logger.debug(f"Disponibilité mise à jour dans la DB: {is_available}")
                    
            finally:
                session.close()
                
        except Exception as e:
            self.logger.error(f"Erreur lors de la mise à jour de disponibilité dans la DB: {e}")
    
    @property
    def name(self) -> str:
        """Retourne le nom du provider."""
        return self.config.get("name", self.provider_id)
    
    @property
    def description(self) -> str:
        """Retourne la description du provider."""
        return self.config.get("description", "")
    
    @property
    def provider_type(self) -> str:
        """Retourne le type de provider (cloud ou local)."""
        return self.config.get("provider_type", "unknown")
    
    @property
    def auth_requirements(self) -> List[Dict[str, Any]]:
        """Retourne la liste des exigences d'authentification."""
        return self.config.get("auth_requirements", [])
    
    @property
    def supported_features(self) -> Dict[str, Any]:
        """Retourne les fonctionnalités prises en charge par le provider."""
        return self.config.get("supported_features", {})
    
    @property
    def default_models(self) -> List[Dict[str, Any]]:
        """Retourne la liste des modèles par défaut du provider."""
        return self.config.get("default_models", [])
    
    @abstractmethod
    def validate_credentials(self, credentials: Dict[str, str]) -> bool:
        """
        Valide les informations d'identification pour ce provider.
        
        Args:
            credentials: Dictionnaire des informations d'identification
            
        Returns:
            True si les informations d'identification sont valides, False sinon
        """
        pass
    
    @abstractmethod
    def get_connection(self, credentials: Dict[str, str]) -> Any:
        """
        Établit une connexion avec le provider en utilisant les informations d'identification.
        
        Args:
            credentials: Dictionnaire des informations d'identification
            
        Returns:
            Objet de connexion spécifique au provider
        """
        pass
    
    @abstractmethod
    def list_available_models(self, credentials: Dict[str, str]) -> List[Dict[str, Any]]:
        """
        Liste les modèles disponibles pour ce provider.
        
        Args:
            credentials: Dictionnaire des informations d'identification
            
        Returns:
            Liste des modèles disponibles avec leurs métadonnées
        """
        pass
    
    @abstractmethod
    def list_fine_tunable_models(self, credentials: Dict[str, str]) -> List[Dict[str, Any]]:
        """
        Liste les modèles qui peuvent être fine-tunés sur ce provider.
        
        Args:
            credentials: Dictionnaire des informations d'identification
            
        Returns:
            Liste des modèles fine-tunables avec leurs métadonnées
        """
        pass
        
    def check_availability(self) -> bool:
        """
        Vérifie si le provider est actuellement disponible et met à jour l'état.
        
        Returns:
            True si le provider est disponible, False sinon
        """
        try:
            # Tenter une opération simple pour vérifier la disponibilité
            from ..core.config_manager import get_provider_config_manager
            
            config_manager = get_provider_config_manager()
            credentials = config_manager.get_provider_config(self.provider_id)
            
            if not credentials:
                self.logger.warning(f"Provider {self.provider_id} non configuré")
                self.is_available = False
                self._update_availability_in_db(False)
                return False
                
            # Essayer de valider les credentials
            is_valid = self.validate_credentials(credentials)
            
            # Mettre à jour l'état de disponibilité
            self.is_available = is_valid
            self._update_availability_in_db(is_valid)
            
            if not is_valid:
                self.logger.warning(f"Credentials invalides pour le provider {self.provider_id}")
                
            return is_valid
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la vérification de disponibilité du provider {self.provider_id}: {e}")
            self.logger.debug("Détails:", exc_info=True)
            self.is_available = False
            self._update_availability_in_db(False)
            return False
    
    def execute_with_error_handling(self, operation_name: str, func, *args, **kwargs):
        """
        Exécute une fonction avec gestion d'erreurs standardisée.
        
        Args:
            operation_name: Nom de l'opération pour les logs
            func: Fonction à exécuter
            *args, **kwargs: Arguments à passer à la fonction
            
        Returns:
            Résultat de la fonction
            
        Raises:
            ProviderError: En cas d'erreur avec le message approprié
        """
        from .exceptions import ProviderError, ProviderConnectionError, ProviderAuthenticationError
        
        if not self.is_available:
            self.logger.warning(f"Tentative d'utilisation du provider {self.provider_id} qui est indisponible")
            raise ProviderError(f"Provider {self.provider_id} est actuellement indisponible")
        
        try:
            self.logger.debug(f"Exécution de {operation_name} sur {self.provider_id}")
            result = func(*args, **kwargs)
            return result
            
        except ProviderError:
            # Si c'est déjà une ProviderError, la propager directement
            raise
            
        except ConnectionError as e:
            self.logger.error(f"Erreur de connexion lors de {operation_name}: {e}")
            self.is_available = False
            self._update_availability_in_db(False)
            raise ProviderConnectionError(f"Erreur de connexion à {self.name}: {str(e)}")
            
        except (ValueError, KeyError) as e:
            self.logger.error(f"Erreur d'authentification lors de {operation_name}: {e}")
            raise ProviderAuthenticationError(f"Erreur d'authentification avec {self.name}: {str(e)}")
            
        except Exception as e:
            self.logger.error(f"Erreur inattendue lors de {operation_name}: {e}")
            self.logger.debug("Détails:", exc_info=True)
            raise ProviderError(f"Erreur avec {self.name}: {str(e)}")
    
    @property
    def type(self) -> str:
        """
        Retourne le type de provider (cloud ou local).
        Rétrocompatible avec l'ancienne API.
        """
        # Déterminer à partir de l'ID du provider (ex: cloud.openai -> cloud)
        parts = self.provider_id.split('.')
        if len(parts) > 0 and parts[0] in ["cloud", "local"]:
            return parts[0]
            
        # Sinon utiliser la valeur dans la configuration
        return self.config.get("provider_type", "unknown")
