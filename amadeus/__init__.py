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
        self.max_logs = 1000  # Limiter la mémoire
        
    def emit(self, record):
        # Capturer TOUS les niveaux, y compris DEBUG
        formatted_record = self.format(record)
        self.logs.append({
            'message': formatted_record,
            'level': record.levelname,
            'timestamp': record.created,
            'logger': record.name
        })
        
        # Limiter la taille pour éviter la surcharge mémoire
        if len(self.logs) > self.max_logs:
            self.logs = self.logs[-self.max_logs:]
        
    def get_logs(self, level_filter=None):
        """Récupère les logs avec filtrage optionnel."""
        if level_filter:
            return [log for log in self.logs if log['level'] == level_filter]
        return [log['message'] for log in self.logs]
        
    def get_error_logs(self):
        """Récupère seulement les erreurs."""
        return [log['message'] for log in self.logs if log['level'] in ['ERROR', 'CRITICAL']]
        
    def get_warning_logs(self):
        """Récupère seulement les warnings."""
        return [log['message'] for log in self.logs if log['level'] == 'WARNING']
    
    def clear_logs(self):
        self.logs.clear()

# Créer un handler mémoire global
memory_handler = MemoryHandler()
memory_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

# Configuration du logging principal - CAPTURER TOUS LES NIVEAUX
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)  # CHANGÉ: capturer DEBUG aussi

# Supprimer tous les handlers existants
for handler in root_logger.handlers[:]:
    root_logger.removeHandler(handler)

# Ajouter seulement notre handler mémoire
root_logger.addHandler(memory_handler)

# Application version
__version__ = "0.2.0"  # Updated version with DB support

def get_stored_logs(level_filter=None):
    """Récupère tous les logs stockés en mémoire avec filtrage optionnel."""
    return memory_handler.get_logs(level_filter)

def get_error_summary():
    """Récupère un résumé des erreurs en mémoire."""
    errors = memory_handler.get_error_logs()
    warnings = memory_handler.get_warning_logs()
    return {
        'errors': errors,
        'warnings': warnings,
        'total_errors': len(errors),
        'total_warnings': len(warnings)
    }

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
