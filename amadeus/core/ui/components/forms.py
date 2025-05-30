from prompt_toolkit.application import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.layout.containers import HSplit, VSplit, Window, FloatContainer, Float
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.widgets import Button, Box, Frame, Label, TextArea, Dialog, Shadow
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.filters import Condition
from prompt_toolkit.validation import Validator
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.layout.margins import ScrollbarMargin
from prompt_toolkit.application.current import get_app

# Optional clipboard support with improved fallback
try:
    import pyperclip
    CLIPBOARD_AVAILABLE = True
    CLIPBOARD_ERROR = None
except ImportError as e:
    CLIPBOARD_AVAILABLE = False
    CLIPBOARD_ERROR = str(e)

def get_clipboard_status():
    """Retourne le statut détaillé du presse-papier."""
    if not CLIPBOARD_AVAILABLE:
        return {
            "available": False,
            "error": CLIPBOARD_ERROR,
            "suggestion": "Installez pyperclip: pip install pyperclip==1.9.0"
        }
    
    # Tester la fonctionnalité
    try:
        # Test simple pour vérifier que pyperclip fonctionne
        test_content = "amadeus_clipboard_test"
        pyperclip.copy(test_content)
        result = pyperclip.paste()
        
        return {
            "available": True,
            "working": result == test_content,
            "method": getattr(pyperclip, '_functions', {}).get('copy', 'unknown')
        }
    except Exception as e:
        return {
            "available": True,
            "working": False,
            "error": str(e),
            "linux_help": "Sur Linux, installez: sudo apt-get install xclip ou xsel"
        }

class Field:
    """Représente un champ dans un formulaire."""
    
    def __init__(self, name, label, default="", secret=False, required=False,
                 description=None, validator=None):
        self.name = name
        self.label = label
        self.default = default
        self.secret = secret
        self.required = required
        self.description = description or ""
        self.validator = validator
        self.value = default
        
    def create_control(self, width=40):
        """Crée un contrôle pour ce champ."""
        # Créer un label pour le champ avec indicateur de modification si nécessaire
        required_indicator = ' *' if self.required else ''
        modified_indicator = ' (modifié)' if self.default and self.secret else ''
        
        field_label = Label(HTML(
            f"<info>{self.label}</info>{required_indicator}{modified_indicator}: "
        ))
        
        # Créer un TextArea pour ce champ avec support du presse-papier
        text_area = TextArea(
            text=self.default,
            password=self.secret,
            multiline=False,
            width=width,
            height=1,
            style="class:input-field",
            validator=self.validator,
            wrap_lines=False
        )
        
        # Fonction pour coller depuis le presse-papier
        def paste_from_clipboard():
            """Colle le contenu du presse-papier dans le champ."""
            if CLIPBOARD_AVAILABLE:
                try:
                    clipboard_content = pyperclip.paste()
                    if clipboard_content:
                        text_area.text = clipboard_content
                        # Rafraîchir l'affichage
                        get_app().invalidate()
                except Exception:
                    # Si erreur, ignorer silencieusement
                    pass
        
        # Créer le bouton Coller seulement si pyperclip est disponible
        paste_button = None
        if CLIPBOARD_AVAILABLE:
            paste_button = Button(
                "📋 Coller",
                handler=paste_from_clipboard,
                width=10
            )
        
        # Ajouter les raccourcis clavier améliorés
        kb = KeyBindings()
        
        if CLIPBOARD_AVAILABLE:
            @kb.add('c-v')
            def paste_from_clipboard_kb(event):
                """Coller depuis le presse-papier avec Ctrl+V"""
                try:
                    clipboard_content = pyperclip.paste()
                    if clipboard_content:
                        # Remplacer le contenu actuel par le contenu du presse-papier
                        event.current_buffer.text = clipboard_content
                        # Placer le curseur à la fin
                        event.current_buffer.cursor_position = len(clipboard_content)
                except Exception:
                    # Si pyperclip n'est pas disponible, ignorer silencieusement
                    pass
            
            @kb.add('c-c')
            def copy_to_clipboard(event):
                """Copier le contenu actuel vers le presse-papier avec Ctrl+C"""
                try:
                    if not self.secret:  # Ne pas copier les champs secrets
                        content = event.current_buffer.text
                        if content:
                            pyperclip.copy(content)
                except Exception:
                    # Si pyperclip n'est pas disponible, ignorer silencieusement
                    pass
        
        # Attacher les raccourcis clavier au TextArea
        text_area.control.key_bindings = kb
        
        # Stocker le TextArea pour récupérer la valeur plus tard
        self.text_area = text_area
        
        # Créer le conteneur avec le champ et le bouton
        if paste_button:
            # Organiser le champ et le bouton côte à côte
            field_container = VSplit([
                field_label,
                text_area,
                Window(width=1),  # Petit espacement
                paste_button
            ])
        else:
            # Pas de bouton si pyperclip n'est pas disponible
            field_container = VSplit([
                field_label,
                text_area
            ])
        
        # Décrire le champ si une description est fournie
        if self.description:
            description_label = Label(HTML(f"<secondary>{self.description}</secondary>"))
            return field_container, description_label
        
        return field_container, None
    
    @property
    def current_value(self):
        """Renvoie la valeur actuelle du champ."""
        if hasattr(self, 'text_area'):
            return self.text_area.text
        return self.value

class Form:
    """Un formulaire interactif pour saisir des données."""
    
    def __init__(self, title, fields=None, on_submit=None, on_cancel=None, width=60):
        self.title = title
        self.fields = fields or []
        self.on_submit = on_submit
        self.on_cancel = on_cancel
        self.width = width
        self.kb = KeyBindings()
        
        # Navigation dans le formulaire
        @self.kb.add('tab')
        def _(event):
            event.app.layout.focus_next()
            
        @self.kb.add('s-tab')
        def _(event):
            event.app.layout.focus_previous()
            
        @self.kb.add('escape')
        def _(event):
            if self.on_cancel:
                self.on_cancel()
            event.app.exit()
    
    def add_field(self, name, label, default="", secret=False, required=False, 
                  description=None, validator=None):
        """Ajoute un champ au formulaire."""
        field = Field(name, label, default, secret, required, description, validator)
        self.fields.append(field)
        return field
    
    def create_form(self):
        """Crée un conteneur de formulaire."""
        form_items = []
        
        # Ajouter des instructions en haut du formulaire avec info améliorée sur le presse-papier
        clipboard_status = get_clipboard_status()
        
        if clipboard_status["available"] and clipboard_status.get("working", True):
            form_items.append(Label(HTML(
                "<info>📋 Presse-papier opérationnel • Ctrl+V: Coller • Ctrl+C: Copier</info>"
            )))
        elif clipboard_status["available"] and not clipboard_status.get("working", True):
            linux_help = clipboard_status.get("linux_help", "")
            form_items.append(Label(HTML(
                f"<warning>⚠️ Presse-papier détecté mais non fonctionnel</warning>"
            )))
            if linux_help:
                form_items.append(Label(HTML(
                    f"<info>💡 {linux_help}</info>"
                )))
        else:
            suggestion = clipboard_status.get("suggestion", "")
            form_items.append(Label(HTML(
                f"<warning>⚠️ Presse-papier non disponible</warning>"
            )))
            if suggestion:
                form_items.append(Label(HTML(
                    f"<info>💡 {suggestion}</info>"
                )))
        
        form_items.append(Label(HTML(
            "<info>Tab/Shift+Tab pour naviguer, Entrée pour soumettre, Échap pour annuler</info>"
        )))
        form_items.append(Window(height=1))  # Espaceur
        
        # Ajouter les champs
        for field in self.fields:
            field_control, description_control = field.create_control(width=self.width-20)
            form_items.append(field_control)
            if description_control:
                form_items.append(description_control)
            form_items.append(Window(height=1))  # Espaceur
        
        # Ajouter les boutons de soumission
        buttons = [
            Button("Soumettre", handler=self._handle_submit),
            Button("Annuler", handler=self._handle_cancel),
        ]
        
        form_items.append(VSplit(buttons, padding=2))
        
        # Construire le conteneur final
        form_container = HSplit(form_items)
        
        # Créer un cadre autour du formulaire
        form_frame = Frame(form_container, title=self.title)
        
        # Centrer le formulaire avec une largeur fixe
        centered_form = Box(
            form_frame,
            padding=1,
            width=Dimension(preferred=self.width + 4),
            height=Dimension(min=len(self.fields) * 3 + 6),
            style="class:dialog"
        )
        
        return centered_form, self.kb
    
    def _handle_submit(self):
        """Récupère les valeurs du formulaire et appelle le callback on_submit."""
        values = {field.name: field.current_value for field in self.fields}
        if self.on_submit:
            self.on_submit(values)
    
    def _handle_cancel(self):
        """Annule le formulaire et appelle le callback on_cancel."""
        if self.on_cancel:
            self.on_cancel()

class NotificationDialog:
    """Dialogue simple pour afficher des notifications."""
    
    def __init__(self, title, text, buttons=None):
        self.title = title
        self.text = text
        self.buttons = buttons or [("✅ OK", lambda: None)]
        self.kb = KeyBindings()
        
        @self.kb.add('escape', 'q')
        def _(event):
            self.buttons[0][1]()  # Exécuter le callback du premier bouton
            event.app.exit()
        
        @self.kb.add('enter', 'space')
        def _(event):
            self.buttons[0][1]()  # Exécuter le callback du premier bouton
            event.app.exit()
    
    def create_dialog(self):
        """Crée un dialogue de notification moderne."""
        # Créer les boutons avec style amélioré
        button_widgets = []
        for i, (label, callback) in enumerate(self.buttons):
            # Ajouter des icônes si pas déjà présentes
            if not any(emoji in label for emoji in ["✅", "❌", "⚠️", "ℹ️", "🔙", "👍", "👎"]):
                if "ok" in label.lower() or "d'accord" in label.lower():
                    label = f"✅ {label}"
                elif any(word in label.lower() for word in ["annuler", "cancel", "non", "no"]):
                    label = f"❌ {label}"
                elif any(word in label.lower() for word in ["retour", "back"]):
                    label = f"🔙 {label}"
                elif any(word in label.lower() for word in ["oui", "yes"]):
                    label = f"👍 {label}"
            
            button = Button(label, handler=callback)
            button_widgets.append(button)
        
        # Créer le contenu du dialogue avec style moderne
        content = HSplit([
            Window(height=1),  # Espacement supérieur
            Label(HTML(f"<dialog-text>{self.text}</dialog-text>")),
            Window(height=2),  # Espacement
            VSplit(button_widgets, padding=3, align="center")
        ])
        
        # Construire le dialogue avec bordures modernes
        dialog_frame = Frame(
            content, 
            title=f" {self.title} ",
            style="class:dialog.modern"
        )
        
        # Centrer le dialogue avec ombre
        try:
            # Essayer d'utiliser Shadow si disponible
            centered_dialog = Box(
                Shadow(dialog_frame),
                padding=2,
                width=Dimension(preferred=max(len(self.text) + 15, 40), max=80),
                style="class:dialog.notification"
            )
        except (ImportError, NameError):
            # Fallback sans ombre si Shadow n'est pas disponible
            centered_dialog = Box(
                dialog_frame,
                padding=2,
                width=Dimension(preferred=max(len(self.text) + 15, 40), max=80),
                style="class:dialog.notification"
            )
        
        return centered_dialog, self.kb
