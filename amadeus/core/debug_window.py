import os
import sys
import subprocess
import threading
import time
import logging
import queue
from typing import Optional, List
from pathlib import Path
import tempfile

class DebugWindow:
    """Gestionnaire de fenêtre de debug en temps réel."""
    
    def __init__(self):
        self.debug_enabled = False
        self.debug_process = None
        self.debug_queue = queue.Queue()
        self.debug_file = None
        self.debug_thread = None
        self.logger = logging.getLogger("amadeus.debug")
        
    def enable_debug_window(self):
        """Active la fenêtre de debug."""
        if self.debug_enabled:
            return True
            
        try:
            # Créer un fichier temporaire pour les logs debug
            self.debug_file = tempfile.NamedTemporaryFile(
                mode='w+', 
                suffix='.log', 
                prefix='amadeus_debug_',
                delete=False
            )
            
            # Démarrer le processus de visualisation
            self._start_debug_viewer()
            
            # Configurer le logging pour écrire dans le fichier debug
            self._setup_debug_logging()
            
            # Démarrer le thread de monitoring
            self._start_debug_thread()
            
            self.debug_enabled = True
            self.logger.info("=== FENÊTRE DEBUG ACTIVÉE ===")
            return True
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'activation du debug: {e}")
            return False
    
    def disable_debug_window(self):
        """Désactive la fenêtre de debug."""
        if not self.debug_enabled:
            return
            
        self.debug_enabled = False
        
        # Arrêter le thread de monitoring
        if self.debug_thread and self.debug_thread.is_alive():
            self.debug_thread.join(timeout=2)
        
        # Fermer le processus de visualisation
        if self.debug_process and self.debug_process.poll() is None:
            self.debug_process.terminate()
            try:
                self.debug_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.debug_process.kill()
        
        # Nettoyer le fichier temporaire
        if self.debug_file:
            try:
                self.debug_file.close()
                os.unlink(self.debug_file.name)
            except:
                pass
        
        self.logger.info("=== FENÊTRE DEBUG DÉSACTIVÉE ===")
    
    def _start_debug_viewer(self):
        """Démarre le processus de visualisation des logs."""
        try:
            # Essayer différents terminaux selon l'OS
            if os.name == 'nt':  # Windows
                cmd = ['cmd', '/c', 'start', 'cmd', '/k', f'type {self.debug_file.name} & timeout /t 1 > nul & goto start']
            elif sys.platform == 'darwin':  # macOS
                cmd = ['osascript', '-e', f'tell app "Terminal" to do script "tail -f {self.debug_file.name}"']
            else:  # Linux/Unix
                # Essayer différents terminaux
                terminals = [
                    ['gnome-terminal', '--', 'tail', '-f', self.debug_file.name],
                    ['konsole', '-e', 'tail', '-f', self.debug_file.name],
                    ['xterm', '-e', 'tail', '-f', self.debug_file.name],
                    ['terminator', '-e', f'tail -f {self.debug_file.name}'],
                ]
                
                for cmd in terminals:
                    try:
                        self.debug_process = subprocess.Popen(
                            cmd,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL
                        )
                        return
                    except FileNotFoundError:
                        continue
                
                # Fallback: utiliser xdg-open avec un script
                self._create_debug_script()
                return
            
            self.debug_process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
        except Exception as e:
            self.logger.error(f"Erreur lors du démarrage du viewer: {e}")
    
    def _create_debug_script(self):
        """Crée un script pour afficher les logs si aucun terminal trouvé."""
        script_content = f"""#!/bin/bash
echo "=== AMADEUS DEBUG WINDOW ==="
echo "Logs en temps réel..."
echo "Appuyez sur Ctrl+C pour quitter"
tail -f {self.debug_file.name}
"""
        script_path = Path(tempfile.gettempdir()) / "amadeus_debug.sh"
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        os.chmod(script_path, 0o755)
        
        try:
            self.debug_process = subprocess.Popen(
                ['xdg-open', str(script_path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except:
            # Dernier recours: afficher les instructions
            print(f"\n=== DEBUG WINDOW ===")
            print(f"Pour voir les logs debug en temps réel, exécutez:")
            print(f"tail -f {self.debug_file.name}")
            print("===================\n")
    
    def _setup_debug_logging(self):
        """Configure le logging pour écrire dans le fichier debug."""
        if not self.debug_file:
            return
            
        # Créer un handler pour le fichier debug
        debug_handler = logging.FileHandler(self.debug_file.name, mode='w')
        debug_handler.setLevel(logging.DEBUG)
        
        # Format détaillé pour le debug
        debug_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)-30s | %(filename)s:%(lineno)d | %(message)s',
            datefmt='%H:%M:%S'
        )
        debug_handler.setFormatter(debug_formatter)
        
        # Ajouter le handler au logger root et amadeus
        logging.getLogger().addHandler(debug_handler)
        logging.getLogger('amadeus').addHandler(debug_handler)
        
        # Configurer le niveau pour capturer tous les messages
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger('amadeus').setLevel(logging.DEBUG)
    
    def _start_debug_thread(self):
        """Démarre le thread de monitoring."""
        def debug_monitor():
            while self.debug_enabled:
                try:
                    # Écrire un heartbeat périodique
                    if self.debug_file and not self.debug_file.closed:
                        self.debug_file.write(f"[{time.strftime('%H:%M:%S')}] DEBUG WINDOW ACTIVE\n")
                        self.debug_file.flush()
                    
                    time.sleep(30)  # Heartbeat toutes les 30 secondes
                    
                except Exception:
                    break
        
        self.debug_thread = threading.Thread(target=debug_monitor, daemon=True)
        self.debug_thread.start()
    
    def log_debug(self, message: str, level: str = "DEBUG"):
        """Ajoute un message debug."""
        if not self.debug_enabled or not self.debug_file:
            return
            
        try:
            timestamp = time.strftime('%H:%M:%S')
            self.debug_file.write(f"[{timestamp}] {level}: {message}\n")
            self.debug_file.flush()
        except Exception:
            pass
    
    def __del__(self):
        """Nettoyage automatique."""
        self.disable_debug_window()

# Instance globale
debug_window = DebugWindow()

def enable_debug_window():
    """Active la fenêtre de debug globale."""
    return debug_window.enable_debug_window()

def disable_debug_window():
    """Désactive la fenêtre de debug globale."""
    debug_window.disable_debug_window()

def is_debug_enabled():
    """Vérifie si le debug est activé."""
    return debug_window.debug_enabled

def debug_log(message: str, level: str = "DEBUG"):
    """Ajoute un message debug."""
    debug_window.log_debug(message, level)
