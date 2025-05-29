from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.application.current import get_app
import logging

logger = logging.getLogger("amadeus.ui.handlers.keys")

def create_global_key_bindings():
    """Crée les raccourcis clavier globaux pour l'application."""
    kb = KeyBindings()
    
    @kb.add('q')
    def quit_app(event):
        """Quitter l'application avec 'q'"""
        logger.info("Utilisateur a quitté avec 'q'")
        event.app.exit()
    
    @kb.add('escape')
    def go_back(event):
        """Retour au menu précédent avec 'escape'"""
        logger.debug("Retour demandé avec 'escape'")
        # Cette logique sera gérée par l'application principale
        pass
    
    @kb.add('c-c')
    def interrupt(event):
        """Interruption avec Ctrl+C"""
        logger.info("Interruption avec Ctrl+C")
        event.app.exit(exception=KeyboardInterrupt)
    
    @kb.add('c-d')
    def eof(event):
        """Sortie avec Ctrl+D"""
        logger.info("Sortie avec Ctrl+D")
        event.app.exit()
    
    @kb.add('f1')
    def show_help(event):
        """Afficher l'aide avec F1"""
        logger.debug("Aide demandée avec F1")
        # À implémenter : affichage de l'aide contextuelle
        pass
    
    return kb

def create_menu_key_bindings():
    """Crée les raccourcis clavier spécifiques aux menus."""
    kb = KeyBindings()
    
    @kb.add('up', 'k')
    def move_up(event):
        """Déplacement vers le haut dans les menus"""
        logger.debug("Navigation vers le haut")
        pass
    
    @kb.add('down', 'j')
    def move_down(event):
        """Déplacement vers le bas dans les menus"""
        logger.debug("Navigation vers le bas")
        pass
    
    @kb.add('enter', 'space')
    def select_item(event):
        """Sélection d'un élément"""
        logger.debug("Sélection d'élément")
        pass
    
    @kb.add('home')
    def go_to_first(event):
        """Aller au premier élément"""
        logger.debug("Navigation vers le premier élément")
        pass
    
    @kb.add('end')
    def go_to_last(event):
        """Aller au dernier élément"""
        logger.debug("Navigation vers le dernier élément")
        pass
    
    return kb

def create_form_key_bindings():
    """Crée les raccourcis clavier spécifiques aux formulaires."""
    kb = KeyBindings()
    
    @kb.add('tab')
    def next_field(event):
        """Champ suivant avec Tab"""
        logger.debug("Champ suivant avec Tab")
        pass
    
    @kb.add('s-tab')
    def previous_field(event):
        """Champ précédent avec Shift+Tab"""
        logger.debug("Champ précédent avec Shift+Tab")
        pass
    
    @kb.add('c-s')
    def save_form(event):
        """Sauvegarder avec Ctrl+S"""
        logger.debug("Sauvegarde demandée avec Ctrl+S")
        pass
    
    return kb
