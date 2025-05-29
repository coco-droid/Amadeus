from prompt_toolkit import Application
from prompt_toolkit.layout.containers import HSplit, VSplit, Window, FloatContainer, Float
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.widgets import Box, Frame, Shadow
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings, merge_key_bindings
from prompt_toolkit.application.current import get_app
from shutil import get_terminal_size
import logging

from amadeus.core.ui.styles import AMADEUS_STYLE, COLORS
from amadeus.core.ui.components.menus import MenuManager
from amadeus.core.ui.screens.main_menu import show_main_menu, show_initial_language_selection
from amadeus.i18n import get_translator, set_language

class AmadeusApp:
    def __init__(self, first_run=True):
        self.menu_manager = MenuManager()
        self.kb = KeyBindings()
        self.menu_kb = None
        self.first_run = first_run
        self.is_main_menu = True
        
        # Configurer les logs pour qu'ils soient silencieux pendant l'UI
        self._configure_silent_logging()
        
        @self.kb.add('q')
        def _(event):
            """Quitter l'application avec 'q'"""
            event.app.exit()
            
        @self.kb.add('escape')
        def _(event):
            """Retour au menu précédent avec 'escape'"""
            menu, kb = self.menu_manager.back_to_previous_menu()
            if menu:
                self.is_main_menu = (len(self.menu_manager.history) == 0)
                self.show_menu_container(menu, kb)
            else:
                self.is_main_menu = True
                self.show_main_menu()
    
    def _configure_silent_logging(self):
        """Configure les logs pour qu'ils soient silencieux pendant l'UI."""
        # Désactiver tous les logs console pendant l'UI
        logging.getLogger().handlers = []
        
        # Garder seulement les logs fichier et mémoire
        from amadeus import memory_handler
        amadeus_logger = logging.getLogger('amadeus')
        amadeus_logger.handlers = [h for h in amadeus_logger.handlers if not isinstance(h, logging.StreamHandler)]
        
        # S'assurer que les logs sont toujours enregistrés en mémoire
        if memory_handler not in amadeus_logger.handlers:
            amadeus_logger.addHandler(memory_handler)
    
    def create_modern_header(self):
        """Crée un en-tête moderne et plus impressionnant pour Amadeus."""
        translator = get_translator()
        
        # Vérifier la largeur du terminal
        try:
            term_width, term_height = get_terminal_size()
        except:
            # En cas d'erreur, utiliser une largeur par défaut
            term_width, term_height = 80, 24
        
        # ASCII Art moderne et adaptatif sans balises HTML
        if term_width >= 80:
            ascii_art = [
                "     ╔══════════════════════════════════════════════════════════════╗",
                "     ║  █████╗ ███╗   ███╗ █████╗ ██████╗ ███████╗██╗   ██╗███████╗  ║",
                "     ║  ██╔══██╗████╗ ████║██╔══██╗██╔══██╗██╔════╝██║   ██║██╔════╝  ║",
                "     ║  ███████║██╔████╔██║███████║██║  ██║█████╗  ██║   ██║███████╗  ║",
                "     ║  ██╔══██║██║╚██╔╝██║██╔══██║██║  ██║██╔══╝  ██║   ██║╚════██║  ║",
                "     ║  ██║  ██║██║ ╚═╝ ██║██║  ██║██████╔╝███████╗╚██████╔╝███████║  ║",
                "     ║  ╚═╝  ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝╚═════╝ ╚══════╝ ╚═════╝ ╚══════╝  ║",
                "     ╚══════════════════════════════════════════════════════════════╝"
            ]
        elif term_width >= 60:
            ascii_art = [
                "╔════════════════════════════════════════════════╗",
                "║  █████╗ ███╗   ███╗ █████╗ ██████╗ ███████╗██╗   ██╗███████╗  ║",
                "║  ██╔══██╗████╗ ████║██╔══██╗██╔══██╗██╔════╝██║   ██║██╔════╝  ║",
                "║  ███████║██╔████╔██║███████║██║  ██║█████╗  ██║   ██║███████╗  ║",
                "║  ██╔══██║██║╚██╔╝██║██╔══██║██║  ██║██╔══╝  ██║   ██║╚════██║  ║",
                "║  ██║  ██║██║ ╚═╝ ██║██║  ██║██████╔╝███████╗╚██████╔╝███████║  ║",
                "║  ╚═╝  ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝╚═════╝ ╚══════╝ ╚═════╝ ╚══════╝  ║",
                "╚════════════════════════════════════════════════╝"
            ]
        else:
            # Version très compacte
            ascii_art = [
                "╔═══════════════════════════════╗",
                "║ 🎻 A M A D E U S   A I ║",
                "╚═══════════════════════════════╝"
            ]
        
        # Titre sous le logo sans balises HTML
        title = translator.get('app_title', 'Assistant IA pour Fine-Tuning')
        subtitle = "🎼 Composez l'intelligence artificielle parfaite 🎼"
        
        # Construire le contenu sans styles HTML
        content = []
        content.extend(ascii_art)
        content.append("")  # Ligne vide
        content.append(title)
        content.append(subtitle)
        
        # Créer un contrôle de texte pour le logo
        logo_control = FormattedTextControl(HTML("\n".join(content)))
        
        # Créer une fenêtre pour le logo avec hauteur adaptée
        logo_window = Window(
            height=len(content),
            content=logo_control,
            align="center"
        )
        
        # Créer un conteneur pour le logo avec style moderne
        logo_container = Box(
            logo_window, 
            padding=Dimension(preferred=1, max=2),
            style="class:header.modern"
        )
        
        return logo_container
    
    def create_compact_header(self):
        """Crée un header compact et moderne pour les sous-menus."""
        translator = get_translator()
        
        # Header compact avec style moderne
        title = translator.get('app_title', 'Amadeus AI')
        compact_header = f"<accent>🎻</accent> <primary>{title}</primary> <secondary>• AI Fine-Tuning Assistant</secondary>"
        
        # Créer un contrôle de texte pour le titre
        title_control = FormattedTextControl(HTML(compact_header))
        
        # Créer une fenêtre pour le titre
        title_window = Window(
            height=1,
            content=title_control,
            align="center"
        )
        
        # Conteneur avec bordure moderne
        title_container = Box(
            title_window, 
            padding=Dimension(preferred=0, max=1),
            style="class:header.compact"
        )
        
        return title_container
    
    def change_language(self, lang_code):
        """Change la langue de l'application."""
        from amadeus.i18n import set_language
        
        # Utiliser le nouveau système qui retourne True/False selon le succès
        if set_language(lang_code):
            # Enregistrer la préférence de langue
            from amadeus.cli import save_language_preference
            save_language_preference(lang_code)
            
            # Retourner au menu principal avec la nouvelle langue
            self.is_main_menu = True  # Le menu principal s'affichera après
            self.show_main_menu()
        else:
            # Afficher un message d'erreur si la langue n'est pas disponible
            from amadeus.core.ui.components.forms import NotificationDialog
            translator = get_translator()
            
            dialog = NotificationDialog(
                title="Erreur",
                text=f"La langue '{lang_code}' n'est pas disponible.",
                buttons=[("OK", lambda: self.show_main_menu())]
            )
            dialog_container, dialog_kb = dialog.create_dialog()
            self.show_dialog_container(dialog_container, dialog_kb)

    def show_main_menu(self):
        """Affiche le menu principal de l'application."""
        self.is_main_menu = True
        show_main_menu(self)
    
    def show_menu_container(self, menu, kb):
        """Affiche un conteneur de menu avec ou sans le logo selon le contexte."""
        # Structure complète de l'interface
        if self.is_main_menu:
            # Menu principal avec logo
            root_container = HSplit([
                self.create_modern_header(),
                menu
            ])
        else:
            # Sous-menu avec header compact
            root_container = HSplit([
                self.create_compact_header(),
                menu
            ])
        
        # Conteneur principal avec centrage mais dimensions flexibles
        # Utiliser un padding minimum pour éviter les problèmes d'affichage
        main_container = Box(
            root_container,
            padding=Dimension(preferred=0, max=1),
            style="class:dialog"
        )
        
        # Création du layout et de l'application
        layout = Layout(main_container)
        
        # Mise à jour des raccourcis clavier
        self.menu_kb = kb
        all_bindings = merge_key_bindings([self.kb, kb]) if kb else self.kb
        
        # Création ou mise à jour de l'application
        if not hasattr(self, 'app') or self.app is None:
            self.app = Application(
                layout=layout,
                full_screen=True,
                mouse_support=True,
                style=AMADEUS_STYLE,
                key_bindings=all_bindings
            )
        else:
            self.app.layout = layout
            self.app.key_bindings = all_bindings

    def show_form_container(self, form, kb):
        """Affiche un formulaire dans un conteneur flottant."""
        # Créer un conteneur flottant pour le formulaire
        float_container = FloatContainer(
            content=HSplit([
                self.create_compact_header(),  # Toujours utiliser le header compact pour les formulaires
                Window()  # Fenêtre vide pour remplir l'espace
            ]),
            floats=[
                Float(
                    content=form,
                    top=2,
                    bottom=2,
                    left=2,
                    right=2
                )
            ]
        )
        
        # Création du layout et de l'application
        layout = Layout(float_container)
        
        # Mise à jour des raccourcis clavier
        all_bindings = merge_key_bindings([self.kb, kb]) if kb else self.kb
        
        # Mise à jour de l'application
        if hasattr(self, 'app') and self.app is not None:
            self.app.layout = layout
            self.app.key_bindings = all_bindings
        else:
            self.app = Application(
                layout=layout,
                full_screen=True,
                mouse_support=True,
                style=AMADEUS_STYLE,
                key_bindings=all_bindings
            )

    def show_dialog_container(self, dialog, kb):
        """Affiche un dialogue dans un conteneur flottant."""
        # Même implémentation que show_form_container, mais avec un style différent
        float_container = FloatContainer(
            content=HSplit([
                self.create_compact_header(),  # Toujours utiliser le header compact pour les dialogs
                Window()  # Fenêtre vide pour remplir l'espace
            ]),
            floats=[
                Float(
                    content=dialog,
                    top=2,
                    bottom=2,
                    left=2,
                    right=2
                )
            ]
        )
        
        # Création du layout et de l'application
        layout = Layout(float_container)
        
        # Mise à jour des raccourcis clavier
        all_bindings = merge_key_bindings([self.kb, kb]) if kb else self.kb
        
        # Mise à jour de l'application
        if hasattr(self, 'app') and self.app is not None:
            self.app.layout = layout
            self.app.key_bindings = all_bindings
        else:
            self.app = Application(
                layout=layout,
                full_screen=True,
                mouse_support=True,
                style=AMADEUS_STYLE,
                key_bindings=all_bindings
            )

    def show_training_options(self, model_type):
        """Affiche les options de configuration pour l'entraînement d'un type de modèle."""
        translator = get_translator()
        
        # Cette fonction sera déplacée vers un module dédié ultérieurement
        self.is_main_menu = False
        options = [
            (f"{translator.get('model_configuration')} {model_type}", lambda: None),
            (f"{translator.get('interactive_mode')} {model_type}", lambda: None),
            (translator.get("menus.return"), lambda: self.show_main_menu())
        ]
        
        title = f"{translator.get('providers.provider_config')} {model_type}"
        menu, kb = self.menu_manager.show_menu(title, options, width=40)
        self.show_menu_container(menu, kb)

    def manage_model(self, action):
        """Gère les opérations sur les modèles."""
        translator = get_translator()
        
        # Cette fonction sera déplacée vers un module dédié ultérieurement
        self.is_main_menu = False
        options = [
            (translator.get("not_implemented"), lambda: None),
            (translator.get("menus.return"), lambda: self.show_main_menu())
        ]
        
        title = f"{translator.get('menus.models_management')} - {action}"
        menu, kb = self.menu_manager.show_menu(title, options, width=50)
        self.show_menu_container(menu, kb)
    
    def run(self):
        """Lance l'application Amadeus."""
        logger = logging.getLogger("amadeus.ui.application")
        
        try:
            logger.info(f"Démarrage de l'application - Premier lancement: {self.first_run}")
            
            if self.first_run:
                # Premier lancement : sélection de la langue
                logger.info("Affichage de la sélection de langue initiale")
                self.is_main_menu = False  # Le sélecteur de langue n'est pas le menu principal
                from amadeus.core.ui.screens.main_menu import show_initial_language_selection
                show_initial_language_selection(self)
            else:
                # Lancements suivants : menu principal directement
                logger.info("Affichage du menu principal")
                self.is_main_menu = True
                self.show_main_menu()
            
            logger.info("Lancement de l'interface utilisateur")
            if hasattr(self, 'app') and self.app is not None:
                self.app.run()
            else:
                logger.error("L'application prompt_toolkit n'a pas été créée correctement")
                
        except Exception as e:
            logger.error(f"Erreur lors du lancement de l'application: {e}")
            logger.exception("Détails de l'erreur:")
            raise
