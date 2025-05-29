import os
import logging
import logging.handlers
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import json
import re
from pathlib import Path

class LogManager:
    """Gestionnaire centralisé des logs pour Amadeus."""
    
    def __init__(self, log_dir: Optional[str] = None):
        """Initialise le gestionnaire de logs.
        
        Args:
            log_dir: Répertoire pour stocker les logs. Par défaut ~/.amadeus/logs
        """
        if log_dir is None:
            home_dir = Path.home()
            self.log_dir = home_dir / '.amadeus' / 'logs'
        else:
            self.log_dir = Path(log_dir)
        
        # Créer le répertoire de logs s'il n'existe pas
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.log_file = self.log_dir / f"amadeus_{datetime.now().strftime('%Y%m%d')}.log"
        self.setup_logging()
    
    def setup_logging(self):
        """Configure le système de logging."""
        # Format des logs
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
        date_format = '%Y-%m-%d %H:%M:%S'
        
        formatter = logging.Formatter(log_format, date_format)
        
        # Logger principal
        logger = logging.getLogger('amadeus')
        logger.setLevel(logging.DEBUG)
        
        # Supprimer les handlers existants pour éviter les doublons
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # Handler pour fichier (rotating)
        file_handler = logging.handlers.RotatingFileHandler(
            self.log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Handler pour console (niveau INFO par défaut)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            '%H:%M:%S'
        ))
        logger.addHandler(console_handler)
        
        # Empêcher la propagation vers le logger root
        logger.propagate = False
        
        return logger
    
    def get_log_files(self) -> List[Path]:
        """Retourne la liste des fichiers de logs disponibles."""
        log_files = []
        for file_path in self.log_dir.glob("amadeus_*.log*"):
            if file_path.is_file():
                log_files.append(file_path)
        return sorted(log_files, key=lambda x: x.stat().st_mtime, reverse=True)
    
    def parse_log_line(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse une ligne de log et retourne un dictionnaire."""
        # Pattern pour parser les logs
        pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) - ([\w\.]+) - (\w+) - ([\w\.]+):(\d+) - (.*)'
        match = re.match(pattern, line.strip())
        
        if match:
            return {
                'timestamp': match.group(1),
                'logger': match.group(2),
                'level': match.group(3),
                'file': match.group(4),
                'line': int(match.group(5)),
                'message': match.group(6)
            }
        return None
    
    def filter_logs(self, 
                   level_filter: Optional[str] = None,
                   logger_filter: Optional[str] = None,
                   date_filter: Optional[str] = None,
                   limit: int = 100,
                   search: Optional[str] = None) -> List[Dict[str, Any]]:
        """Filtre les logs selon les critères spécifiés.
        
        Args:
            level_filter: Niveau de log à filtrer (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            logger_filter: Nom du logger à filtrer
            date_filter: Date au format YYYY-MM-DD
            limit: Nombre maximum de lignes à retourner
            search: Terme à rechercher dans les messages
            
        Returns:
            Liste des logs filtrés
        """
        logs = []
        log_files = self.get_log_files()
        
        # Déterminer quels fichiers examiner selon le filtre de date
        files_to_check = log_files
        if date_filter:
            try:
                target_date = datetime.strptime(date_filter, '%Y-%m-%d')
                date_str = target_date.strftime('%Y%m%d')
                files_to_check = [f for f in log_files if date_str in f.name]
            except ValueError:
                pass  # Ignorer les dates invalides
        
        for log_file in files_to_check:
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        parsed = self.parse_log_line(line)
                        if not parsed:
                            continue
                        
                        # Filtrer par niveau
                        if level_filter and parsed['level'].upper() != level_filter.upper():
                            continue
                        
                        # Filtrer par logger
                        if logger_filter and logger_filter.lower() not in parsed['logger'].lower():
                            continue
                        
                        # Filtrer par recherche de texte
                        if search and search.lower() not in parsed['message'].lower():
                            continue
                        
                        logs.append(parsed)
                        
                        # Limiter le nombre de résultats
                        if len(logs) >= limit:
                            break
                    
                    if len(logs) >= limit:
                        break
                        
            except Exception as e:
                # Logger l'erreur mais continuer
                logging.getLogger('amadeus.logging').error(f"Erreur lecture fichier {log_file}: {e}")
        
        # Trier par timestamp (plus récent en premier)
        logs.sort(key=lambda x: x['timestamp'], reverse=True)
        return logs[:limit]
    
    def cleanup_old_logs(self, days_to_keep: int = 30):
        """Supprime les logs plus anciens que le nombre de jours spécifié."""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        for log_file in self.get_log_files():
            try:
                file_date = datetime.fromtimestamp(log_file.stat().st_mtime)
                if file_date < cutoff_date:
                    log_file.unlink()
                    logging.getLogger('amadeus.logging').info(f"Log supprimé: {log_file}")
            except Exception as e:
                logging.getLogger('amadeus.logging').error(f"Erreur suppression {log_file}: {e}")

class LogViewer:
    """Interface pour visualiser les logs."""
    
    def __init__(self, log_manager: LogManager):
        self.log_manager = log_manager
    
    def format_log_entry(self, log_entry: Dict[str, Any], colorize: bool = True) -> str:
        """Formate une entrée de log pour l'affichage."""
        level = log_entry['level']
        timestamp = log_entry['timestamp']
        logger = log_entry['logger']
        message = log_entry['message']
        location = f"{log_entry['file']}:{log_entry['line']}"
        
        if colorize:
            # Codes couleur ANSI
            colors = {
                'DEBUG': '\033[36m',    # Cyan
                'INFO': '\033[32m',     # Vert
                'WARNING': '\033[33m',  # Jaune
                'ERROR': '\033[31m',    # Rouge
                'CRITICAL': '\033[35m', # Magenta
                'RESET': '\033[0m'      # Reset
            }
            
            color = colors.get(level, '')
            reset = colors['RESET']
            
            return f"{color}[{timestamp}] {level:<8} {logger:<20} {location:<20} {message}{reset}"
        else:
            return f"[{timestamp}] {level:<8} {logger:<20} {location:<20} {message}"
    
    def display_logs(self, logs: List[Dict[str, Any]], colorize: bool = True):
        """Affiche une liste de logs."""
        if not logs:
            print("Aucun log trouvé avec les critères spécifiés.")
            return
        
        print(f"\n{'='*80}")
        print(f"Affichage de {len(logs)} entrées de log")
        print(f"{'='*80}")
        
        for log_entry in logs:
            print(self.format_log_entry(log_entry, colorize))
        
        print(f"{'='*80}")
    
    def display_summary(self):
        """Affiche un résumé des logs."""
        log_files = self.log_manager.get_log_files()
        
        print(f"\n{'='*50}")
        print("RÉSUMÉ DES LOGS AMADEUS")
        print(f"{'='*50}")
        print(f"Répertoire des logs: {self.log_manager.log_dir}")
        print(f"Nombre de fichiers: {len(log_files)}")
        
        if log_files:
            print(f"Fichier le plus récent: {log_files[0].name}")
            
            # Statistiques par niveau
            stats = {'DEBUG': 0, 'INFO': 0, 'WARNING': 0, 'ERROR': 0, 'CRITICAL': 0}
            
            for level in stats.keys():
                logs = self.log_manager.filter_logs(level_filter=level, limit=1000)
                stats[level] = len(logs)
            
            print("\nStatistiques par niveau:")
            for level, count in stats.items():
                print(f"  {level:<10}: {count}")
        
        print(f"{'='*50}")

def setup_logging(log_dir: Optional[str] = None) -> LogManager:
    """Configure le système de logging global pour Amadeus."""
    return LogManager(log_dir)

def get_log_viewer(log_manager: Optional[LogManager] = None) -> LogViewer:
    """Retourne une instance de LogViewer."""
    if log_manager is None:
        log_manager = LogManager()
    return LogViewer(log_manager)
