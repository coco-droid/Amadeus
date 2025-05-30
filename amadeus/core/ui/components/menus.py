from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.layout import HSplit, VSplit, Window, FormattedTextControl
from prompt_toolkit.layout.containers import FloatContainer, Float, ConditionalContainer
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.widgets import Box, Button, Frame, Label, Shadow
from prompt_toolkit.application.current import get_app
from prompt_toolkit import Application
from prompt_toolkit.key_binding import KeyBindings
from shutil import get_terminal_size

class ModernButton(Button):
    """Un bouton moderne avec un meilleur rendu et support de navigation."""
    
    def __init__(self, text="", handler=None, width=None, key=None):
        super().__init__(text=text, handler=handler, width=width)
        self.key = key  # Pour permettre la navigation clavier
        
        # Style amélioré avec ombres et bordures
        style = "class:button"
        self.window.style = style
        
    def set_focus(self, focus):
        """Change l'état de focus du bouton."""
        self.control.focusable = focus

class MainMenu:
    def __init__(self, title="Menu Principal", options=None, width=40):
        self.title = title
        self.options = options or []
        self.selected_option = 0
        
        # Largeur adaptative avec minimum esthétique
        try:
            term_width, _ = get_terminal_size()
            self.width = min(max(width, 35), term_width - 15)  # Marges optimisées
        except:
            self.width = max(width, 35)
            
        self.buttons = []
        self.kb = KeyBindings()
        
        # Raccourcis clavier améliorés pour la navigation dans le menu
        @self.kb.add('up', 'k')
        def _(event):
            self._select_previous()
            
        @self.kb.add('down', 'j')
        def _(event):
            self._select_next()
            
        @self.kb.add('enter', 'space')
        def _(event):
            self._activate_selected()
            
        # Raccourcis numériques pour sélection rapide
        for i in range(1, 10):
            @self.kb.add(str(i))
            def _(event, index=i-1):
                if 0 <= index < len(self.buttons):
                    self.selected_option = index
                    get_app().layout.focus(self.buttons[self.selected_option])
                    self._activate_selected()
    
    def _select_previous(self):
        """Sélectionne l'option précédente dans le menu."""
        if self.buttons:
            self.selected_option = (self.selected_option - 1) % len(self.buttons)
            get_app().layout.focus(self.buttons[self.selected_option])
    
    def _select_next(self):
        """Sélectionne l'option suivante dans le menu."""
        if self.buttons:
            self.selected_option = (self.selected_option + 1) % len(self.buttons)
            get_app().layout.focus(self.buttons[self.selected_option])
    
    def _activate_selected(self):
        """Active l'option sélectionnée."""
        if self.buttons and 0 <= self.selected_option < len(self.buttons):
            button = self.buttons[self.selected_option]
            if button.handler:
                button.handler()
        
    def create_menu(self):
        """Crée un menu élégant et parfaitement centré avec design moderne."""
        menu_buttons = []
        self.buttons = []
        
        # Instructions de navigation simplifiées sans balises HTML
        nav_help = Label(
            "════════════════════════════════════════\n"
            " Navigation • ↑↓/kj Navigate • ⏎/Space Select • 1-9 Quick\n"
            " • Esc Back • Q Quit • Tab Next Field (forms)\n"
            "════════════════════════════════════════"
        )
        
        menu_buttons.append(nav_help)
        menu_buttons.append(Window(height=1))  # Espacement
        
        # Boutons du menu avec numérotation simple
        for i, (option_text, callback) in enumerate(self.options):
            # Construire le texte du bouton sans emojis automatiques ni balises HTML
            # Les emojis sont déjà dans les traductions
            button_text = f"{i+1}. {option_text}"
            
            button = ModernButton(
                text=button_text,
                handler=callback,
                width=self.width
            )
            menu_buttons.append(button)
            self.buttons.append(button)
            
            # Ajouter un petit espacement entre les boutons
            if i < len(self.options) - 1:
                menu_buttons.append(Window(height=Dimension(preferred=0, max=1)))
        
        # Conteneur avec espacement approprié et padding amélioré
        menu_container = HSplit(menu_buttons, padding=Dimension(preferred=1, max=2))
        
        # Frame avec titre stylé et bordures modernes
        title_with_style = f" {self.title} "
        menu_frame = Frame(
            menu_container,
            title=title_with_style,
            style="class:frame.modern"
        )
        
        # Box pour le centrage avec ombre et style moderne
        centered_menu = Box(
            Shadow(menu_frame),  # Ombre portée
            padding=Dimension(preferred=1, max=2),
            width=Dimension(preferred=self.width + 10, max=self.width + 15),
            style="class:dialog.modern"
        )
        
        return centered_menu, self.kb

class MenuManager:
    def __init__(self):
        self.current_menu = None
        self.current_kb = None
        self.history = []
        
    def show_menu(self, title, options, width=40):
        """Affiche un menu avec les options spécifiées."""
        # Adapter la largeur au terminal de façon agressive
        try:
            term_width, _ = get_terminal_size()
            # Utiliser une largeur très contrainte si nécessaire
            menu_width = min(width, max(20, term_width - 10))
        except:
            # Fallback avec largeur minimale
            menu_width = min(width, 30)
            
        # Sauvegarder le menu actuel dans l'historique si existant
        if self.current_menu is not None:
            self.history.append((self.current_menu, self.current_kb))
            
        # Créer un nouveau menu
        menu = MainMenu(title=title, options=options, width=menu_width)
        self.current_menu, self.current_kb = menu.create_menu()
        
        return self.current_menu, self.current_kb
        
    def back_to_previous_menu(self):
        """Retourne au menu précédent."""
        if self.history:
            self.current_menu, self.current_kb = self.history.pop()
            return self.current_menu, self.current_kb
        return None, None
        
    def clear_history(self):
        """Efface l'historique des menus."""
        self.history = []
        
    def back_to_main_menu(self):
        """Retourne au menu principal."""
        self.clear_history()  # Effacer l'historique
        # Implémentation à compléter, pour l'instant on quitte
        get_app().exit()
