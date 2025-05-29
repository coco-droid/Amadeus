# This makes 'amadeus' a recognized Python package
"""
Amadeus - An AI Assistant Framework
"""

import logging
import os
import sys
from io import StringIO

# Configurer un système de logging qui capture les messages sans les afficher immédiatement
class MemoryHandler(logging.Handler):
    """Handler qui stocke les logs en mémoire pour les afficher plus tard."""
    
    def __init__(self):
        super().__init__()
        self.logs = []
        
    def emit(self, record):
        self.logs.append(self.format(record))
        
    def get_logs(self):
        return self.logs
        
    def clear_logs(self):
        self.logs.clear()

# Créer un handler mémoire global
memory_handler = MemoryHandler()
memory_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

# Configuration du logging principal - utiliser seulement le handler mémoire
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# Supprimer tous les handlers existants
for handler in root_logger.handlers[:]:
    root_logger.removeHandler(handler)

# Ajouter seulement notre handler mémoire
root_logger.addHandler(memory_handler)

# Application version
__version__ = "0.2.0"  # Updated version with DB support

def get_stored_logs():
    """Récupère tous les logs stockés en mémoire."""
    return memory_handler.get_logs()

def clear_stored_logs():
    """Efface tous les logs stockés en mémoire."""
    memory_handler.clear_logs()

def print_stored_logs():
    """Affiche tous les logs stockés dans la console."""
    logs = get_stored_logs()
    if logs:
        print("\n" + "="*80)
        print("📋 LOGS D'EXÉCUTION AMADEUS")
        print("="*80)
        for log in logs:
            # Ajouter des icônes selon le niveau de log
            if "ERROR" in log:
                print(f"❌ {log}")
            elif "WARNING" in log:
                print(f"⚠️ {log}")
            elif "INFO" in log:
                print(f"ℹ️ {log}")
            elif "DEBUG" in log:
                print(f"🐛 {log}")
            else:
                print(f"📝 {log}")
        print("="*80 + "\n")

def configure_ui_logging():
    """Configure les logs pour qu'ils soient silencieux pendant l'UI."""
    # Supprimer tous les handlers console existants
    root_logger = logging.getLogger()
    console_handlers = [h for h in root_logger.handlers if isinstance(h, logging.StreamHandler)]
    for handler in console_handlers:
        root_logger.removeHandler(handler)
    
    # Garder seulement le handler mémoire
    if memory_handler not in root_logger.handlers:
        root_logger.addHandler(memory_handler)
    
    # Configuration spéciale pour le logger amadeus
    amadeus_logger = logging.getLogger('amadeus')
    amadeus_console_handlers = [h for h in amadeus_logger.handlers if isinstance(h, logging.StreamHandler)]
    for handler in amadeus_console_handlers:
        amadeus_logger.removeHandler(handler)
    
    # S'assurer que le handler mémoire est présent
    if memory_handler not in amadeus_logger.handlers:
        amadeus_logger.addHandler(memory_handler)

# Initialize configuration and database on import
def initialize_app():
    """Initialize the application environment"""
    try:
        # Create necessary directories first
        os.makedirs(os.path.expanduser("~/.amadeus"), exist_ok=True)
        
        # Try to initialize configuration
        try:
            from amadeus.core.config_manager import init_config
            init_config()
        except ImportError as e:
            if 'sqlalchemy' in str(e).lower():
                logging.warning("SQLAlchemy not installed. Database features will be disabled.")
            else:
                logging.error(f"Error initializing configuration: {e}")
        except Exception as e:
            logging.error(f"Error initializing configuration: {e}")
        
        # Try to initialize database (optional)
        try:
            from amadeus.database.session import init_db
            init_db()
        except ImportError as e:
            if 'sqlalchemy' in str(e).lower():
                logging.info("Database features disabled (SQLAlchemy not installed)")
            else:
                logging.error(f"Error initializing database: {e}")
        except Exception as e:
            logging.error(f"Error initializing database: {e}")
            
    except Exception as e:
        logging.error(f"Error during application initialization: {e}")
        # Continue even if there's an error, as some parts may still work

# Run initialization
initialize_app()

# Configuration des logs silencieux par défaut
configure_ui_logging()
