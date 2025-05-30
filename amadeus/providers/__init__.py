"""
Module de gestion des providers pour Amadeus.

Ce module contient les classes et fonctions pour gérer les différents
providers de modèles d'IA que ce soit en local ou sur le cloud.

Pour ajouter un nouveau provider:
1. Créez un répertoire dans 'local/' ou 'cloud/' selon le type
2. Ajoutez un fichier 'provider.py' avec une classe héritant de Provider
3. Ajoutez un fichier 'config.json' avec la configuration
4. Le provider sera automatiquement découvert au démarrage
"""

import os
import sys
import logging
from typing import Dict, Any, List, Tuple, Optional
import json

# Configuration du logging
logger = logging.getLogger("amadeus.providers")

# S'assurer que le package est importable
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, os.path.dirname(current_dir))

# Importation des modules de base
try:
    from .base import Provider
    from .registry import ProviderRegistry
    from .exceptions import (
        ProviderError, ProviderNotFoundError,
        ProviderConnectionError, ProviderAuthenticationError,
        ProviderConfigurationError
    )
    from .db_config import DBProviderConfigManager

    # Initialiser le registre global des providers
    registry = ProviderRegistry()
    
    # Utiliser le gestionnaire de base de données par défaut pour les credentials sécurisés
    config_manager = DBProviderConfigManager()
    
    # VÉRIFICATION AUTOMATIQUE DES PROVIDERS AU DÉMARRAGE
    def _startup_provider_verification():
        """Vérifie les providers au démarrage d'Amadeus."""
        try:
            logger.info("=== AMADEUS STARTUP: Provider Verification ===")
            
            # Importer ici pour éviter les imports circulaires
            from .registry import verify_and_sync_providers
            
            verification_result = verify_and_sync_providers()
            
            if verification_result["status"] == "error":
                logger.error(f"Provider verification failed: {verification_result['message']}")
                return False
            
            logger.info(f"Provider verification completed:")
            logger.info(f"  Total in registry: {verification_result.get('total_registry', 0)}")
            logger.info(f"  Total in database: {verification_result.get('total_database', 0)}")
            logger.info(f"  New providers found: {len(verification_result.get('new_providers', []))}")
            logger.info(f"  Missing providers: {len(verification_result.get('missing_providers', []))}")
            
            if verification_result.get('new_providers'):
                logger.info(f"New providers: {verification_result['new_providers']}")
            
            if verification_result.get('missing_providers'):
                logger.warning(f"Missing providers (in DB but not discovered): {verification_result['missing_providers']}")
            
            return True
            
        except Exception as e:
            logger.error(f"Startup provider verification failed: {e}")
            logger.debug("Startup verification error details:", exc_info=True)
            return False
    
    # Exécuter la vérification au démarrage
    _startup_verification_success = _startup_provider_verification()
    
    if not _startup_verification_success:
        logger.warning("Provider verification failed during startup, some features may not work correctly")

    # APIs publiques simplifiées
    def get_all_providers(only_available: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Retourne tous les providers disponibles.
        
        Args:
            only_available: Si True, ne retourne que les providers disponibles
            
        Returns:
            Dictionnaire des providers avec leurs configurations
        """
        try:
            # Récupérer les providers découverts par le registry
            if only_available:
                discovered_providers = registry.get_available_providers()
                logger.debug(f"Providers disponibles du registry: {list(discovered_providers.keys())}")
            else:
                discovered_providers = registry.get_all_providers()
                logger.debug(f"Tous les providers du registry: {list(discovered_providers.keys())}")
            
            # Récupérer les providers configurés
            configured_provider_ids = config_manager.get_all_providers()
            logger.debug(f"Providers configurés: {configured_provider_ids}")
            
            # Combiner les informations
            result = {}
            
            # Ajouter les providers découverts
            for provider_id, config in discovered_providers.items():
                result[provider_id] = config.copy()
                # Marquer comme configuré si présent dans le config manager
                result[provider_id]['is_configured'] = provider_id in configured_provider_ids
            
            # Ajouter les providers configurés qui ne sont pas dans le registry
            for provider_id in configured_provider_ids:
                if provider_id not in result:
                    # Provider configuré mais pas découvert - peut-être supprimé ou indisponible
                    result[provider_id] = {
                        "name": provider_id.split('.')[-1].title(),
                        "description": "Configured provider (not discovered)",
                        "provider_type": "unknown",
                        "is_configured": True,
                        "is_available": False,
                        "version": "unknown"
                    }
            
            # S'assurer que les providers sont enregistrés dans la DB
            if hasattr(config_manager, 'ensure_provider_exists'):
                for provider_id, config in result.items():
                    config_manager.ensure_provider_exists(
                        provider_id, 
                        config.get('name'), 
                        config.get('provider_type')
                    )
            
            logger.info(f"Total providers retournés: {len(result)}")
            return result
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des providers: {e}")
            logger.debug("Détails de l'erreur:", exc_info=True)
            return {}

    def get_cloud_providers(only_available: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Retourne les providers cloud disponibles.
        """
        try:
            logger.debug(f"Getting cloud providers (only_available={only_available})")
            
            # Forcer la synchronisation DB si nécessaire
            if not hasattr(registry, '_last_sync_time'):
                logger.info("Forcing database sync for cloud providers")
                force_database_sync()
            
            all_providers = get_all_providers(only_available)
            providers = {k: v for k, v in all_providers.items() if v.get('provider_type') == 'cloud'}
            logger.info(f"Cloud providers found: {list(providers.keys())}")
            
            # Debug détaillé si aucun provider trouvé
            if not providers:
                logger.warning("No cloud providers found! Starting detailed debugging...")
                
                # Obtenir le résumé du registry
                if hasattr(registry, 'get_providers_summary'):
                    summary = registry.get_providers_summary()
                    logger.info(f"Registry summary: {summary}")
                
                # Vérifier la structure des répertoires
                providers_dir = os.path.dirname(os.path.abspath(__file__))
                cloud_dir = os.path.join(providers_dir, 'cloud')
                if os.path.exists(cloud_dir):
                    cloud_items = [item for item in os.listdir(cloud_dir) if os.path.isdir(os.path.join(cloud_dir, item)) and not item.startswith('__')]
                    logger.info(f"Cloud directory contains: {cloud_items}")
                    
                    for item in cloud_items:
                        item_path = os.path.join(cloud_dir, item)
                        config_file = os.path.join(item_path, 'config.json')
                        provider_file = os.path.join(item_path, 'provider.py')
                        logger.info(f"  {item}: config.json={os.path.exists(config_file)}, provider.py={os.path.exists(provider_file)}")
                else:
                    logger.error(f"Cloud directory does not exist: {cloud_dir}")
                
                # Redécouvrir les providers
                logger.info("Attempting to rediscover providers...")
                refresh_providers()
                
                # Essayer à nouveau
                all_providers = get_all_providers(only_available)
                providers = {k: v for k, v in all_providers.items() if v.get('provider_type') == 'cloud'}
                logger.info(f"After rediscovery, cloud providers: {list(providers.keys())}")
            
            return providers
        except Exception as e:
            logger.error(f"Error getting cloud providers: {e}")
            logger.debug("Cloud providers error details:", exc_info=True)
            return {}

    def get_local_providers(only_available: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Retourne les providers locaux disponibles.
        """
        try:
            logger.debug(f"Getting local providers (only_available={only_available})")
            
            all_providers = get_all_providers(only_available)
            providers = {k: v for k, v in all_providers.items() if v.get('provider_type') == 'local'}
            logger.info(f"Local providers found: {list(providers.keys())}")
            
            # Debug si aucun provider local trouvé
            if not providers:
                logger.warning("No local providers found!")
                providers_dir = os.path.dirname(os.path.abspath(__file__))
                local_dir = os.path.join(providers_dir, 'local')
                if os.path.exists(local_dir):
                    local_items = [item for item in os.listdir(local_dir) if os.path.isdir(os.path.join(local_dir, item)) and not item.startswith('__')]
                    logger.info(f"Local directory contains: {local_items}")
                else:
                    logger.error(f"Local directory does not exist: {local_dir}")
            
            return providers
        except Exception as e:
            logger.error(f"Error getting local providers: {e}")
            return {}
    
    def refresh_providers():
        """
        Force la redécouverte des providers.
        Utile pour recharger après l'ajout de nouveaux providers.
        """
        global registry
        try:
            logger.info("Redécouverte des providers...")
            registry = ProviderRegistry()
            logger.info("Redécouverte terminée")
        except Exception as e:
            logger.error(f"Erreur lors de la redécouverte: {e}")

    def force_database_sync():
        """
        Force la synchronisation avec la base de données.
        """
        try:
            logger.info("Forçage de la synchronisation avec la base de données...")
            registry.force_database_sync()
            logger.info("Synchronisation terminée")
        except Exception as e:
            logger.error(f"Erreur lors de la synchronisation DB: {e}")

    def get_database_status():
        """
        Retourne l'état de la base de données des providers.
        """
        try:
            if hasattr(registry, 'get_database_status'):
                return registry.get_database_status()
            else:
                logger.error("Registry does not have get_database_status method")
                return {"error": "get_database_status method not available in registry"}
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du statut DB: {e}")
            return {"error": str(e)}

    def debug_provider_discovery():
        """
        Fonction de debug pour diagnostiquer les problèmes de découverte.
        """
        logger.info("=== DEBUG: Découverte des providers ===")
        
        try:
            # Forcer la synchronisation DB d'abord
            force_database_sync()
            
            # Exécuter le debug du registry
            if hasattr(registry, 'debug_providers'):
                registry.debug_providers()
            
            # Afficher le statut de la base de données
            db_status = get_database_status()
            logger.info("=== DATABASE STATUS ===")
            logger.info(f"Total in registry: {db_status.get('total_in_registry', 0)}")
            logger.info(f"Total in database: {db_status.get('total_in_database', 0)}")
            logger.info(f"In registry only: {db_status.get('in_registry_only', [])}")
            logger.info(f"In database only: {db_status.get('in_database_only', [])}")
            logger.info(f"Synchronized: {db_status.get('synchronized', [])}")
            
            if 'database_providers' in db_status:
                logger.info("Database providers:")
                for provider in db_status['database_providers']:
                    logger.info(f"  {provider['provider_id']}: {provider['name']} ({provider['type']}) - Available: {provider['available']}, Configured: {provider['configured']}")
            
            # Afficher la structure des répertoires
            base_path = os.path.dirname(os.path.abspath(__file__))
            logger.info(f"Répertoire de base: {base_path}")
            
            for provider_type in ["cloud", "local"]:
                type_path = os.path.join(base_path, provider_type)
                logger.info(f"\nRépertoire {provider_type}: {type_path}")
                
                if os.path.exists(type_path):
                    items = os.listdir(type_path)
                    logger.info(f"Contenu: {items}")
                    
                    for item in items:
                        item_path = os.path.join(type_path, item)
                        if os.path.isdir(item_path):
                            sub_items = os.listdir(item_path)
                            logger.info(f"  {item}/: {sub_items}")
                            
                            # Vérifier les fichiers essentiels
                            provider_py = os.path.join(item_path, "provider.py")
                            config_json = os.path.join(item_path, "config.json")
                            logger.info(f"    provider.py exists: {os.path.exists(provider_py)}")
                            logger.info(f"    config.json exists: {os.path.exists(config_json)}")
                            
                            if os.path.exists(config_json):
                                try:
                                    with open(config_json, 'r') as f:
                                        config = json.load(f)
                                    logger.info(f"    config content: {config.get('name', 'No name')} ({config.get('provider_type', 'No type')})")
                                except Exception as e:
                                    logger.error(f"    Error reading config: {e}")
                else:
                    logger.warning(f"Répertoire {provider_type} n'existe pas")
            
            # Afficher les providers découverts
            all_providers = registry.get_all_providers()
            logger.info(f"\nProviders découverts: {list(all_providers.keys())}")
            
            for provider_id, config in all_providers.items():
                logger.info(f"  {provider_id}: {config.get('name', 'Sans nom')} ({config.get('provider_type', 'Type inconnu')})")
                
        except Exception as e:
            logger.error(f"Erreur lors du debug: {e}")
            logger.debug("Détails:", exc_info=True)

    def clear_database_providers():
        """
        Supprime tous les providers de la base de données (pour le debug).
        """
        try:
            from ..database.session import get_session
            from ..database.models import Provider as DBProvider, ProviderCredential
            
            session = get_session()
            try:
                # Supprimer d'abord les credentials
                deleted_credentials = session.query(ProviderCredential).delete()
                # Puis les providers
                deleted_providers = session.query(DBProvider).delete()
                session.commit()
                
                logger.info(f"Supprimé {deleted_providers} providers et {deleted_credentials} credentials de la DB")
                return {"deleted_providers": deleted_providers, "deleted_credentials": deleted_credentials}
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Erreur lors de la suppression des providers DB: {e}")
            return {"error": str(e)}

    def rebuild_database():
        """
        Reconstruit complètement la base de données des providers.
        """
        try:
            logger.info("Reconstruction de la base de données des providers...")
            
            # Supprimer tous les providers existants
            clear_result = clear_database_providers()
            logger.info(f"Suppression: {clear_result}")
            
            # Redécouvrir tous les providers
            refresh_providers()
            
            # Forcer la synchronisation
            force_database_sync()
            
            # Vérifier le résultat
            status = get_database_status()
            logger.info(f"Reconstruction terminée: {status.get('total_in_database', 0)} providers en DB")
            
            return status
            
        except Exception as e:
            logger.error(f"Erreur lors de la reconstruction: {e}")
            return {"error": str(e)}

    def get_startup_verification_status() -> Dict[str, Any]:
        """Retourne le statut de la vérification au démarrage."""
        return {
            "verification_completed": _startup_verification_success,
            "current_status": registry.verify_providers_integrity() if _startup_verification_success else {"status": "failed"}
        }

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
        def create_provider(self, _): raise Exception("Cannot create provider: registry not available")
        def get_database_status(self): return {"error": "Registry not available"}
    registry = DummyRegistry()
    
    class DummyConfigManager:
        def get_all_providers(self): return []
        def get_provider_config(self, _): return {}
        def save_provider_config(self, _, __): pass
        def delete_provider_config(self, _): return False
        def check_provider_configured(self, _): return False
    config_manager = DummyConfigManager()
    
    # Variables de fallback
    _startup_verification_success = False
    
    # APIs factices
    def get_all_providers(only_available=False): return {}
    def get_cloud_providers(only_available=False): return {}
    def get_local_providers(only_available=False): return {}
    def refresh_providers(): pass
    def debug_provider_discovery(): pass
    def get_database_status(): return {"error": "Provider system not initialized"}
    def force_database_sync(): pass
    def clear_database_providers(): return {"error": "Provider system not initialized"}
    def rebuild_database(): return {"error": "Provider system not initialized"}
    def get_startup_verification_status():
        return {"verification_completed": False, "error": "Provider system not initialized"}

__all__ = [
    # Classes principales
    'Provider', 'ProviderRegistry',
    # Exceptions
    'ProviderError', 'ProviderNotFoundError', 'ProviderConnectionError',
    'ProviderAuthenticationError', 'ProviderConfigurationError',
    # Instances globales
    'registry', 'config_manager',
    # APIs publiques
    'get_all_providers', 'get_cloud_providers', 'get_local_providers',
    'check_provider_availability', 'get_provider_quick_info',
    'list_provider_types', 'search_providers',
    # Fonctions utilitaires
    'refresh_providers', 'debug_provider_discovery',
    # Nouvelles fonctions de debug DB
    'force_database_sync', 'get_database_status', 'clear_database_providers', 'rebuild_database',
    # Fonction d'état de santé
    'get_provider_health_status',
    # Nouvelles fonctions
    'verify_and_sync_providers', 'get_startup_verification_status',
]
