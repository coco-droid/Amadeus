"""
Core configuration module for Amadeus application.
Provides centralized configuration initialization and management.
"""
import os
import sys
import logging
from typing import Optional, Dict, Any

# Utiliser le logger sans configuration supplémentaire
logger = logging.getLogger(__name__)

# Flag to control whether to use the DB-backed configuration
USE_DB_CONFIG = True

def get_provider_config_manager():
    """
    Factory function that returns the appropriate configuration manager.
    Handles the transition between file-based and DB-backed configurations.
    
    Returns:
        A provider configuration manager instance
    """
    if USE_DB_CONFIG:
        try:
            from ..database.session import init_db
            from ..providers.db_config import DBProviderConfigManager
            
            # Initialize the database if needed
            init_db()
            
            logger.debug("Using database-backed provider configuration manager")
            return DBProviderConfigManager()
            
        except ImportError as e:
            if 'sqlalchemy' in str(e).lower():
                logger.warning("SQLAlchemy not installed. Falling back to file-based configuration")
            else:
                logger.error(f"Failed to initialize database configuration: {e}")
                logger.warning("Falling back to file-based configuration")
            from ..providers.config import ProviderConfigManager
            return ProviderConfigManager()
        except Exception as e:
            logger.error(f"Failed to initialize database configuration: {e}")
            logger.warning("Falling back to file-based configuration")
            from ..providers.config import ProviderConfigManager
            return ProviderConfigManager()
    else:
        # Use the old file-based configuration manager
        logger.debug("Using file-based provider configuration manager")
        from ..providers.config import ProviderConfigManager
        return ProviderConfigManager()

def init_config():
    """
    Initialize the application configuration.
    Sets up necessary directories and configuration files.
    """
    # Ensure the Amadeus home directory exists
    amadeus_home = os.path.expanduser("~/.amadeus")
    os.makedirs(amadeus_home, exist_ok=True)
    
    # Vérifier le presse-papier et donner des conseils si nécessaire
    _check_and_advise_clipboard()
    
    # Other initialization tasks can be added here
    
    # Initialize database if using DB config
    if USE_DB_CONFIG:
        try:
            from ..database.session import init_db
            init_db()
        except ImportError as e:
            if 'sqlalchemy' in str(e).lower():
                logger.warning("SQLAlchemy not installed. Database features disabled.")
            else:
                logger.error(f"Failed to initialize database: {e}")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")

def _check_and_advise_clipboard():
    """Vérifie le presse-papier et donne des conseils d'installation si nécessaire."""
    try:
        import pyperclip
        # Test simple
        pyperclip.copy("test")
        result = pyperclip.paste()
        if result == "test":
            logger.debug("Presse-papier pyperclip fonctionnel")
        else:
            logger.warning("Presse-papier pyperclip détecté mais test échoué")
            if os.name == 'posix':  # Linux/Unix
                logger.info("Sur Linux, installez: sudo apt-get install xclip (ou xsel)")
    except ImportError:
        logger.info("Presse-papier non disponible. Pour l'activer: pip install pyperclip==1.9.0")
        if os.name == 'posix':  # Linux/Unix
            logger.info("Sur Linux, installez aussi: sudo apt-get install xclip")
    except Exception as e:
        logger.warning(f"Problème avec le presse-papier: {e}")
        if os.name == 'posix':  # Linux/Unix
            logger.info("Sur Linux, essayez: sudo apt-get install xclip xsel")

def check_migration_needed() -> bool:
    """
    Check if migration from file-based to DB config is needed.
    
    Returns:
        True if migration is needed, False otherwise
    """
    if not USE_DB_CONFIG:
        return False
        
    try:
        # Check if old config file exists and has data
        from ..providers.config import ProviderConfigManager
        old_config = ProviderConfigManager()
        old_providers = old_config.get_all_providers()
        
        if not old_providers:
            return False
            
        # Check if new DB config has providers
        from ..providers.db_config import DBProviderConfigManager
        new_config = DBProviderConfigManager()
        new_providers = new_config.get_all_providers()
        
        # Migration needed if there are old configs but no new configs
        return len(old_providers) > 0 and len(new_providers) == 0
        
    except ImportError as e:
        if 'sqlalchemy' in str(e).lower():
            logger.debug("SQLAlchemy not available, migration not needed")
        return False
    except Exception as e:
        logger.error(f"Error checking migration status: {e}")
        return False

def run_migration():
    """
    Run the migration from file-based to DB-backed configuration.
    """
    try:
        logger.info("Starting configuration migration...")
        
        # Import and run the migration script
        from ..database.migrate_config import migrate_configurations
        migrate_configurations()
        
        logger.info("Configuration migration completed.")
        return True
    except ImportError as e:
        if 'sqlalchemy' in str(e).lower():
            logger.warning("SQLAlchemy not available, cannot run migration")
        return False
    except Exception as e:
        logger.error(f"Migration error: {e}")
        return False
