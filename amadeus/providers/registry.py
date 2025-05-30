"""
Provider registry implementation
"""

import json
import logging
import os
import importlib.util
import traceback
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger("amadeus.providers.registry")

class ProviderRegistry:
    """Registry pour découvrir et gérer les providers de manière robuste."""
    
    def __init__(self):
        """Initialise le registry et découvre automatiquement les providers."""
        self.providers = {}
        self.config_cache = {}
        self.discovery_errors = []
        self.last_discovery_time = None
        
        # Effectuer la découverte initiale
        self._discover_all_providers()
        
        # Synchroniser avec la base de données
        self._sync_with_database()
        
        # Vérifier le statut du presse-papier au démarrage
        self._check_clipboard_status()
    
    def _check_clipboard_status(self):
        """Vérifie et log le statut du presse-papier."""
        try:
            from ..core.ui.components.forms import get_clipboard_status
            status = get_clipboard_status()
            
            if status["available"] and status.get("working", True):
                logger.debug("Presse-papier opérationnel")
            elif status["available"]:
                logger.warning(f"Presse-papier détecté mais non fonctionnel: {status.get('error', 'Raison inconnue')}")
                if "linux_help" in status:
                    logger.info(f"Aide Linux: {status['linux_help']}")
            else:
                logger.info(f"Presse-papier non disponible: {status.get('suggestion', 'pyperclip manquant')}")
                
        except Exception as e:
            logger.debug(f"Erreur lors de la vérification du presse-papier: {e}")
    
    def _discover_all_providers(self):
        """Découvre tous les providers disponibles de manière récursive."""
        logger.info("=== DÉBUT DÉCOUVERTE DES PROVIDERS ===")
        self.discovery_errors.clear()
        
        try:
            # Obtenir le chemin de base du projet (pas du venv)
            # Remonter jusqu'au répertoire racine du projet
            current_path = Path(__file__).parent
            project_root = current_path
            
            # Si on est dans le venv, trouver le vrai répertoire source
            if 'venv' in str(current_path) or 'site-packages' in str(current_path):
                # Chercher le répertoire source du projet
                possible_paths = [
                    Path.cwd() / "amadeus" / "providers",  # Si lancé depuis la racine
                    Path(__file__).parents[3] / "amadeus" / "providers",  # Remonter de plusieurs niveaux
                    Path.home() / "Desktop" / "Amadeus" / "amadeus" / "providers"  # Chemin absolu connu
                ]
                
                for path in possible_paths:
                    if path.exists() and (path / "cloud").exists():
                        project_root = path
                        break
                else:
                    # Fallback: utiliser le chemin actuel
                    project_root = current_path
            
            providers_base_path = project_root
            logger.info(f"Chemin de base des providers: {providers_base_path}")
            
            # Scanner les dossiers cloud et local
            for provider_type in ['cloud', 'local']:
                type_path = providers_base_path / provider_type
                logger.info(f"Scanning {provider_type} providers dans: {type_path}")
                
                if not type_path.exists():
                    logger.warning(f"Répertoire {provider_type} n'existe pas: {type_path}")
                    continue
                
                # Scan récursif du répertoire
                self._scan_provider_directory(type_path, provider_type)
            
            logger.info(f"Découverte terminée. {len(self.providers)} providers trouvés.")
            
            if self.discovery_errors:
                logger.warning(f"{len(self.discovery_errors)} erreurs lors de la découverte:")
                for error in self.discovery_errors:
                    logger.error(f"  - {error}")
            
        except Exception as e:
            error_msg = f"Erreur critique lors de la découverte: {e}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            self.discovery_errors.append(error_msg)
    
    def _scan_provider_directory(self, directory: Path, provider_type: str):
        """Scanne récursivement un répertoire pour trouver des providers."""
        try:
            logger.debug(f"Scanning directory: {directory}")
            
            # Parcourir tous les éléments du répertoire
            for item in directory.iterdir():
                if item.is_dir() and not item.name.startswith('__'):
                    logger.debug(f"Examining subdirectory: {item.name}")
                    
                    # Chercher un fichier config.json dans ce dossier
                    config_file = item / "config.json"
                    
                    if config_file.exists():
                        logger.debug(f"Found config.json in {item.name}")
                        self._load_provider_from_config(config_file, provider_type, item.name)
                    else:
                        # Vérifier s'il y a un provider.py (provider sans config)
                        provider_py = item / "provider.py"
                        if provider_py.exists():
                            logger.debug(f"Found provider.py without config.json in {item.name}, creating default config")
                            self._create_default_config_and_load(item, provider_type, item.name)
                        else:
                            # Scan récursif si pas de config trouvé
                            logger.debug(f"No config.json or provider.py in {item.name}, scanning recursively")
                            self._scan_provider_directory(item, provider_type)
                        
        except Exception as e:
            error_msg = f"Erreur lors du scan de {directory}: {e}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            self.discovery_errors.append(error_msg)
    
    def _create_default_config_and_load(self, provider_dir: Path, provider_type: str, provider_name: str):
        """Crée une configuration par défaut pour un provider sans config.json."""
        try:
            provider_id = f"{provider_type}.{provider_name}"
            
            # Configuration par défaut
            default_config = {
                "id": provider_id,
                "name": provider_name.title(),
                "type": provider_type,
                "description": f"Provider {provider_name.title()}",
                "version": "1.0.0",
                "supported_tasks": ["chat", "completion"],
                "requires_api_key": True,
                "credentials_schema": {
                    "api_key": {"type": "string", "required": True}
                }
            }
            
            # Créer le fichier config.json
            config_file = provider_dir / "config.json"
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Created default config for {provider_id}")
            
            # Charger la configuration
            self._load_provider_from_config(config_file, provider_type, provider_name)
            
        except Exception as e:
            error_msg = f"Erreur lors de la création de config par défaut pour {provider_name}: {e}"
            logger.error(error_msg)
            self.discovery_errors.append(error_msg)
    
    def _load_provider_from_config(self, config_file: Path, provider_type: str, provider_name: str):
        """Charge un provider depuis son fichier de configuration."""
        try:
            logger.debug(f"Loading provider config from: {config_file}")
            
            # Charger le fichier JSON
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Valider la configuration
            provider_id = config.get('id')
            if not provider_id:
                error_msg = f"ID manquant dans {config_file}"
                logger.error(error_msg)
                self.discovery_errors.append(error_msg)
                return
            
            # Vérifier cohérence de l'ID
            expected_prefix = f"{provider_type}."
            if not provider_id.startswith(expected_prefix):
                logger.warning(f"ID {provider_id} ne commence pas par {expected_prefix}")
            
            # Enrichir la configuration
            config['provider_type'] = provider_type
            config['discovery_path'] = str(config_file.parent)
            config['config_file'] = str(config_file)
            config['is_available'] = True
            
            # Vérifier si le module Python existe
            provider_py = config_file.parent / "provider.py"
            config['has_python_module'] = provider_py.exists()
            
            if not config['has_python_module']:
                logger.debug(f"Pas de module Python pour {provider_id}")
            
            # Stocker dans le registry
            self.providers[provider_id] = config
            self.config_cache[provider_id] = config
            
            logger.info(f"Provider découvert: {provider_id} ({config.get('name', 'Sans nom')})")
            
        except json.JSONDecodeError as e:
            error_msg = f"JSON invalide dans {config_file}: {e}"
            logger.error(error_msg)
            self.discovery_errors.append(error_msg)
        except Exception as e:
            error_msg = f"Erreur lors du chargement de {config_file}: {e}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            self.discovery_errors.append(error_msg)
    
    def _sync_with_database(self):
        """Synchronise les providers découverts avec la base de données."""
        try:
            from ..database.session import get_session
            from ..database.models import Provider as DBProvider
            
            session = get_session()
            try:
                logger.debug("Synchronisation avec la base de données...")
                
                # Obtenir tous les providers de la DB
                db_providers = {p.provider_id: p for p in session.query(DBProvider).all()}
                
                # Ajouter/mettre à jour les providers découverts
                for provider_id, config in self.providers.items():
                    if provider_id in db_providers:
                        # Mettre à jour
                        db_provider = db_providers[provider_id]
                        db_provider.name = config.get('name', provider_id)
                        db_provider.provider_type = config.get('provider_type', 'unknown')
                        db_provider.is_available = True
                    else:
                        # Créer nouveau
                        db_provider = DBProvider(
                            provider_id=provider_id,
                            name=config.get('name', provider_id),
                            provider_type=config.get('provider_type', 'unknown'),
                            is_available=True,
                            is_configured=False
                        )
                        session.add(db_provider)
                
                # Marquer comme indisponibles les providers qui ne sont plus découverts
                for provider_id, db_provider in db_providers.items():
                    if provider_id not in self.providers:
                        db_provider.is_available = False
                
                session.commit()
                logger.info("Synchronisation DB terminée")
                
            finally:
                session.close()
                
        except ImportError:
            logger.debug("Base de données non disponible, synchronisation ignorée")
        except Exception as e:
            logger.error(f"Erreur lors de la synchronisation DB: {e}")
            logger.error(traceback.format_exc())
    
    def get_all_providers(self) -> Dict[str, Dict[str, Any]]:
        """Retourne tous les providers découverts."""
        return self.providers.copy()
    
    def get_available_providers(self) -> Dict[str, Dict[str, Any]]:
        """Retourne seulement les providers disponibles."""
        return {pid: config for pid, config in self.providers.items() 
                if config.get('is_available', False)}
    
    def get_cloud_providers(self) -> Dict[str, Dict[str, Any]]:
        """Retourne les providers cloud."""
        return {pid: config for pid, config in self.providers.items() 
                if config.get('provider_type') == 'cloud'}
    
    def get_local_providers(self) -> Dict[str, Dict[str, Any]]:
        """Retourne les providers locaux."""
        return {pid: config for pid, config in self.providers.items() 
                if config.get('provider_type') == 'local'}
    
    def get_provider_config(self, provider_id: str) -> Optional[Dict[str, Any]]:
        """Retourne la configuration d'un provider spécifique."""
        return self.providers.get(provider_id)
    
    def force_rediscovery(self):
        """Force une nouvelle découverte des providers."""
        logger.info("Redécouverte forcée des providers...")
        self.providers.clear()
        self.config_cache.clear()
        self._discover_all_providers()
        self._sync_with_database()
    
    def get_discovery_status(self) -> Dict[str, Any]:
        """Retourne le statut de la découverte."""
        return {
            'total_discovered': len(self.providers),
            'cloud_providers': len(self.get_cloud_providers()),
            'local_providers': len(self.get_local_providers()),
            'discovery_errors': self.discovery_errors.copy(),
            'providers': list(self.providers.keys())
        }
    
    def force_database_sync(self):
        """Force une synchronisation avec la base de données."""
        logger.info("Synchronisation forcée avec la base de données...")
        self._sync_with_database()
    
    def get_database_status(self) -> Dict[str, Any]:
        """Retourne le statut de synchronisation avec la base de données."""
        try:
            from ..database.session import get_session
            from ..database.models import Provider as DBProvider
            
            session = get_session()
            try:
                db_providers = {p.provider_id: p for p in session.query(DBProvider).all()}
                
                registry_ids = set(self.providers.keys())
                db_ids = set(db_providers.keys())
                
                return {
                    'total_registry': len(registry_ids),
                    'total_database': len(db_ids),
                    'in_registry_only': list(registry_ids - db_ids),
                    'in_database_only': list(db_ids - registry_ids),
                    'synchronized': list(registry_ids & db_ids)
                }
            finally:
                session.close()
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du statut DB: {e}")
            return {
                'error': str(e),
                'total_registry': len(self.providers),
                'total_database': 0,
                'in_registry_only': list(self.providers.keys()),
                'in_database_only': [],
                'synchronized': []
            }

def verify_and_sync_providers():
    """Fonction utilitaire pour vérifier et synchroniser les providers."""
    try:
        registry = ProviderRegistry()
        status = registry.get_discovery_status()
        
        return {
            'status': 'success',
            'total_registry': status['total_discovered'],
            'cloud_providers': status['cloud_providers'],
            'local_providers': status['local_providers'],
            'errors': status['discovery_errors'],
            'providers': status['providers']
        }
    except Exception as e:
        logger.error(f"Erreur lors de la vérification: {e}")
        return {
            'status': 'error',
            'message': str(e)
        }
