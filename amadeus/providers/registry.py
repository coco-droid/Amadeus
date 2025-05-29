import os
import importlib
import importlib.util
import json
import sys
import logging
from typing import Dict, List, Optional, Any, Set
import pkgutil

from amadeus.providers.base import Provider
from amadeus.providers.exceptions import ProviderNotFoundError

class ProviderRegistry:
    """
    Registre des providers disponibles dans l'application.
    Permet de découvrir, instancier et gérer les providers.
    """
    
    def __init__(self):
        """Initialise le registre des providers."""
        self._providers: Dict[str, type] = {}
        self._provider_configs: Dict[str, Dict[str, Any]] = {}
        self._provider_availability: Dict[str, bool] = {}
        self._logger = logging.getLogger("amadeus.providers.registry")
        self._discover_providers()
    
    def _discover_providers(self):
        """
        Découvre automatiquement tous les providers disponibles.
        Explore les sous-packages local/ et cloud/ pour trouver les providers.
        """
        self._logger.info("Démarrage de la découverte des providers...")
        
        try:
            # Import explicite des packages pour éviter les problèmes d'importation
            from amadeus.providers import local, cloud
            
            # Découvrir les providers locaux
            local_count = self._discover_package_providers(local, "local")
            
            # Découvrir les providers cloud
            cloud_count = self._discover_package_providers(cloud, "cloud")
            
            self._logger.info(f"Découverte terminée: {local_count} providers locaux, {cloud_count} providers cloud")
            
        except ImportError as e:
            self._logger.error(f"Erreur lors de l'import des packages providers: {e}")
            self._logger.debug(f"Détails de l'erreur:", exc_info=True)
    
    def _discover_package_providers(self, package, provider_type: str) -> int:
        """
        Découvre les providers dans un package spécifique.
        
        Args:
            package: Package à explorer (local ou cloud)
            provider_type: Type de provider ("local" ou "cloud")
            
        Returns:
            Nombre de providers découverts dans ce package
        """
        discovered_count = 0
        
        try:
            package_path = os.path.dirname(package.__file__)
            self._logger.debug(f"Exploration du package {provider_type} dans {package_path}")
            
            # Explorer chaque sous-package (chaque dossier est un provider)
            for _, name, is_pkg in pkgutil.iter_modules([package_path]):
                if is_pkg:
                    # Vérifier s'il y a un module provider.py et un fichier config.json
                    provider_module_path = os.path.join(package_path, name, "provider.py")
                    config_path = os.path.join(package_path, name, "config.json")
                    
                    # Créer l'identifiant unique du provider
                    provider_id = f"{provider_type}.{name}"
                    
                    # Vérifier la structure
                    self._validate_provider_structure(provider_id, provider_module_path, config_path)
                    
                    if os.path.exists(provider_module_path) and os.path.exists(config_path):
                        try:
                            # Charger la configuration
                            with open(config_path, 'r', encoding='utf-8') as f:
                                try:
                                    config = json.load(f)
                                    # Valider la configuration minimale requise
                                    if not self._validate_config_schema(provider_id, config):
                                        continue
                                except json.JSONDecodeError as e:
                                    self._logger.error(f"Erreur de format JSON dans {config_path}: {e}")
                                    continue
                            
                            # Stocker la configuration même si l'import échoue
                            self._provider_configs[provider_id] = config
                            
                            # Charger dynamiquement le module provider.py
                            try:
                                module_name = f"amadeus.providers.{provider_type}.{name}.provider"
                                provider_module = importlib.import_module(module_name)
                                
                                # Chercher une classe qui hérite de Provider
                                found_provider = False
                                for attr_name in dir(provider_module):
                                    attr = getattr(provider_module, attr_name)
                                    if (isinstance(attr, type) and 
                                        issubclass(attr, Provider) and 
                                        attr != Provider):
                                        self._providers[provider_id] = attr
                                        found_provider = True
                                        discovered_count += 1
                                        self._logger.info(f"Provider découvert: {provider_id}")
                                        self._provider_availability[provider_id] = True
                                        break
                                
                                if not found_provider:
                                    self._logger.warning(f"Aucune classe Provider trouvée dans {module_name}")
                                    self._provider_availability[provider_id] = False
                                    
                            except ImportError as e:
                                self._logger.error(f"Erreur d'importation du module {module_name}: {e}")
                                self._provider_availability[provider_id] = False
                                
                        except Exception as e:
                            self._logger.error(f"Erreur lors du chargement du provider {name}: {e}")
                            self._logger.debug(f"Détails de l'erreur:", exc_info=True)
                            self._provider_availability[provider_id] = False
        
        except Exception as e:
            self._logger.error(f"Erreur lors de la découverte des providers dans {provider_type}: {e}")
            self._logger.debug(f"Détails de l'erreur:", exc_info=True)
            
        return discovered_count
    
    def _validate_provider_structure(self, provider_id: str, module_path: str, config_path: str) -> bool:
        """
        Valide la structure d'un provider.
        
        Args:
            provider_id: Identifiant du provider
            module_path: Chemin du module provider.py
            config_path: Chemin du fichier config.json
            
        Returns:
            True si la structure est valide, False sinon
        """
        missing = []
        if not os.path.exists(module_path):
            missing.append("provider.py")
        if not os.path.exists(config_path):
            missing.append("config.json")
            
        if missing:
            self._logger.warning(f"Provider {provider_id} incomplet, fichiers manquants: {', '.join(missing)}")
            return False
        return True
        
    def _validate_config_schema(self, provider_id: str, config: Dict) -> bool:
        """
        Valide le schéma de la configuration d'un provider.
        
        Args:
            provider_id: Identifiant du provider
            config: Configuration du provider
            
        Returns:
            True si la configuration est valide, False sinon
        """
        required_fields = ["name", "version", "description", "models"]
        missing = [field for field in required_fields if field not in config]
        
        if missing:
            self._logger.warning(f"Configuration incomplète pour {provider_id}, champs manquants: {', '.join(missing)}")
            return False
        return True
    
    def get_provider_class(self, provider_id: str) -> type:
        """
        Récupère la classe du provider spécifié.
        
        Args:
            provider_id: Identifiant du provider
            
        Returns:
            Classe du provider
            
        Raises:
            ProviderNotFoundError: Si le provider n'est pas trouvé
        """
        if provider_id not in self._providers:
            raise ProviderNotFoundError(f"Provider '{provider_id}' non trouvé")
            
        # Vérifier si le provider est disponible
        if not self.is_provider_available(provider_id):
            self._logger.warning(f"Tentative d'accès à un provider indisponible: {provider_id}")
        
        return self._providers[provider_id]
    
    def create_provider(self, provider_id: str) -> Provider:
        """
        Crée une instance du provider spécifié.
        
        Args:
            provider_id: Identifiant du provider
            
        Returns:
            Instance du provider
            
        Raises:
            ProviderNotFoundError: Si le provider n'est pas trouvé
        """
        provider_class = self.get_provider_class(provider_id)
        
        # Vérifier et mettre à jour l'état de disponibilité du provider dans la DB
        try:
            from ..database.session import get_session
            from ..database.models import Provider as DBProvider
            
            session = get_session()
            try:
                db_provider = session.query(DBProvider).filter(DBProvider.provider_id == provider_id).first()
                
                if db_provider:
                    # Mettre à jour l'état de disponibilité
                    self._provider_availability[provider_id] = db_provider.is_available
                    
                    if not db_provider.is_available:
                        self._logger.warning(f"Attention: Provider {provider_id} est marqué comme indisponible dans la base de données")
                        
            finally:
                session.close()
        except Exception as e:
            self._logger.error(f"Erreur lors de la vérification de l'état du provider {provider_id} dans la DB: {e}")
        
        # Créer l'instance
        provider = provider_class(provider_id)
        self._logger.debug(f"Instance du provider {provider_id} créée")
        return provider
    
    def is_provider_available(self, provider_id: str) -> bool:
        """
        Vérifie si un provider est disponible.
        
        Args:
            provider_id: Identifiant du provider
            
        Returns:
            True si le provider est disponible, False sinon
        """
        # Vérifier si le provider existe et est disponible
        if provider_id not in self._provider_availability:
            return False
            
        return self._provider_availability.get(provider_id, False)
    
    def update_provider_availability(self, provider_id: str, is_available: bool):
        """
        Met à jour l'état de disponibilité d'un provider.
        
        Args:
            provider_id: Identifiant du provider
            is_available: True si le provider est disponible, False sinon
        """
        if provider_id in self._provider_configs:
            self._provider_availability[provider_id] = is_available
            self._logger.info(f"Mise à jour de la disponibilité du provider {provider_id}: {'disponible' if is_available else 'indisponible'}")
            
            # Mettre à jour l'état dans la base de données
            try:
                from ..database.session import get_session
                from ..database.models import Provider as DBProvider
                
                session = get_session()
                try:
                    db_provider = session.query(DBProvider).filter(DBProvider.provider_id == provider_id).first()
                    
                    if db_provider:
                        db_provider.is_available = is_available
                        session.commit()
                    else:
                        self._logger.warning(f"Provider {provider_id} non trouvé dans la base de données pour mise à jour de disponibilité")
                        
                finally:
                    session.close()
            except Exception as e:
                self._logger.error(f"Erreur lors de la mise à jour de disponibilité du provider {provider_id} dans la DB: {e}")
    
    def get_all_providers(self) -> Dict[str, Dict[str, Any]]:
        """
        Retourne tous les providers disponibles avec leur configuration.
        
        Returns:
            Dictionnaire des providers avec leurs configurations
        """
        return self._provider_configs
    
    def get_available_providers(self) -> Dict[str, Dict[str, Any]]:
        """
        Retourne uniquement les providers disponibles avec leur configuration.
        
        Returns:
            Dictionnaire des providers disponibles avec leurs configurations
        """
        return {provider_id: config for provider_id, config in self._provider_configs.items() 
                if self.is_provider_available(provider_id)}
    
    def get_providers_by_type(self, provider_type: str, only_available: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Retourne les providers du type spécifié avec leur configuration.
        
        Args:
            provider_type: Type de provider ("local" ou "cloud")
            only_available: Si True, ne retourne que les providers disponibles
            
        Returns:
            Dictionnaire des providers du type spécifié avec leurs configurations
        """
        if only_available:
            return {provider_id: config for provider_id, config in self._provider_configs.items() 
                    if provider_id.startswith(provider_type) and self.is_provider_available(provider_id)}
        else:
            return {provider_id: config for provider_id, config in self._provider_configs.items() 
                    if provider_id.startswith(provider_type)}
    
    def get_provider_config(self, provider_id: str) -> Dict[str, Any]:
        """
        Récupère la configuration d'un provider spécifique.
        
        Args:
            provider_id: Identifiant du provider
            
        Returns:
            Configuration du provider
            
        Raises:
            ProviderNotFoundError: Si le provider n'est pas trouvé
        """
        if provider_id not in self._provider_configs:
            raise ProviderNotFoundError(f"Provider '{provider_id}' non trouvé")
        
        return self._provider_configs[provider_id]
    
    def get_provider_names(self, only_available: bool = False) -> List[str]:
        """
        Récupère la liste des noms de tous les providers.
        
        Args:
            only_available: Si True, ne retourne que les providers disponibles
            
        Returns:
            Liste des noms des providers
        """
        if only_available:
            return [config.get("name", provider_id) 
                    for provider_id, config in self._provider_configs.items()
                    if self.is_provider_available(provider_id)]
        else:
            return [config.get("name", provider_id) 
                    for provider_id, config in self._provider_configs.items()]
