"""
Module de gestion des providers pour Amadeus.

Ce module contient les classes et fonctions pour gérer les différents
providers de modèles d'IA que ce soit en local ou sur le cloud.
"""

import os
import sys
import logging
from typing import Dict, Any, List, Tuple, Optional

# Configuration du logging
logger = logging.getLogger("amadeus.providers")

# S'assurer que le package est importable
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, os.path.dirname(current_dir))

# Importation des modules nécessaires
try:
    from .base import Provider
    from .registry import ProviderRegistry
    from .exceptions import (
        ProviderError, ProviderNotFoundError,
        ProviderConnectionError, ProviderAuthenticationError,
        ProviderConfigurationError
    )

    # Importation des sous-packages pour la découverte automatique
    try:
        from amadeus.providers import cloud, local
    except ImportError as e:
        logger.error(f"Erreur lors de l'import des sous-packages: {e}")
        logger.debug("Détails de l'erreur:", exc_info=True)
        # Créer des modules vides si l'import échoue
        import types
        if 'amadeus.providers.cloud' not in sys.modules:
            sys.modules['amadeus.providers.cloud'] = types.ModuleType('amadeus.providers.cloud')
            sys.modules['amadeus.providers.cloud'].__file__ = os.path.join(current_dir, 'cloud', '__init__.py')
        if 'amadeus.providers.local' not in sys.modules:
            sys.modules['amadeus.providers.local'] = types.ModuleType('amadeus.providers.local')
            sys.modules['amadeus.providers.local'].__file__ = os.path.join(current_dir, 'local', '__init__.py')

    # Initialiser le registre global des providers
    registry = ProviderRegistry()
    
    # Initialiser le gestionnaire de configuration global
    # Utiliser la factory pour obtenir le gestionnaire approprié (DB ou fichier)
    from ..core.config_manager import get_provider_config_manager
    config_manager = get_provider_config_manager()

    # Fonction utilitaire pour obtenir tous les providers disponibles
    def get_all_providers(only_available: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Retourne tous les providers disponibles.
        
        Args:
            only_available: Si True, ne retourne que les providers disponibles
            
        Returns:
            Dictionnaire des providers avec leurs configurations
        """
        if only_available:
            providers = registry.get_available_providers()
            logger.debug(f"Providers disponibles uniquement: {list(providers.keys())}")
        else:
            providers = registry.get_all_providers()
            logger.debug(f"Tous les providers: {list(providers.keys())}")
        return providers

    # Fonction utilitaire pour obtenir les providers par type
    def get_cloud_providers(only_available: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Retourne les providers cloud disponibles.
        
        Args:
            only_available: Si True, ne retourne que les providers disponibles
            
        Returns:
            Dictionnaire des providers cloud avec leurs configurations
        """
        providers = registry.get_providers_by_type("cloud", only_available)
        logger.debug(f"Providers cloud: {list(providers.keys())}")
        return providers

    def get_local_providers(only_available: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Retourne les providers locaux disponibles.
        
        Args:
            only_available: Si True, ne retourne que les providers disponibles
            
        Returns:
            Dictionnaire des providers locaux avec leurs configurations
        """
        providers = registry.get_providers_by_type("local", only_available)
        logger.debug(f"Providers locaux: {list(providers.keys())}")
        return providers
        
    def check_provider_availability(provider_id: str) -> Tuple[bool, str]:
        """
        Vérifie si un provider est disponible et retourne un message explicatif.
        
        Args:
            provider_id: Identifiant du provider à vérifier
            
        Returns:
            Tuple (disponibilité, message)
        """
        try:
            # Vérifier si le provider existe dans le registre
            if provider_id not in registry.get_all_providers():
                return False, f"Provider '{provider_id}' introuvable dans le registre"
                
            # Vérifier s'il est déjà marqué comme indisponible
            if not registry.is_provider_available(provider_id):
                return False, f"Provider '{provider_id}' est marqué comme indisponible"
                
            # Créer une instance du provider et vérifier sa disponibilité
            try:
                provider = registry.create_provider(provider_id)
                is_available = provider.check_availability()
                
                if is_available:
                    return True, f"Provider '{provider_id}' est disponible"
                else:
                    return False, f"Provider '{provider_id}' n'est pas disponible"
                    
            except Exception as e:
                logger.error(f"Erreur lors de la vérification du provider {provider_id}: {e}")
                return False, f"Erreur lors de la vérification: {str(e)}"
                
        except Exception as e:
            logger.error(f"Erreur inattendue lors de la vérification du provider {provider_id}: {e}")
            return False, f"Erreur inattendue: {str(e)}"

except ImportError as e:
    logger.error(f"Erreur critique lors de l'initialisation du package providers: {e}")
    logger.debug("Détails de l'erreur critique:", exc_info=True)
    
    # Créer des objets factices en cas d'erreur critique
    class DummyRegistry:
        def get_all_providers(self): return {}
        def get_available_providers(self): return {}
        def get_providers_by_type(self, _, only_available=False): return {}
        def get_provider_config(self, _): raise Exception("Provider registry not available")
        def is_provider_available(self, _): return False
    registry = DummyRegistry()
    
    class DummyConfigManager:
        def get_all_providers(self): return []
        def get_provider_config(self, _): return {}
        def save_provider_config(self, _, __): pass
        def delete_provider_config(self, _): return False
    config_manager = DummyConfigManager()
    
    def get_all_providers(only_available=False): return {}
    def get_cloud_providers(only_available=False): return {}
    def get_local_providers(only_available=False): return {}
    def check_provider_availability(provider_id): return False, "Système des providers non initialisé"

__all__ = [
    'Provider', 'ProviderRegistry',
    'ProviderError', 'ProviderNotFoundError', 'ProviderConnectionError',
    'ProviderAuthenticationError', 'ProviderConfigurationError',
    'registry', 'config_manager', 'get_all_providers',    'get_cloud_providers', 'get_local_providers', 'check_provider_availability'
]
