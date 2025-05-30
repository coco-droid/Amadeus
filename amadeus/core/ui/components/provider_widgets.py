"""
Composants UI spécialisés pour la gestion des providers.
"""

import logging
from typing import Dict, List, Any, Optional, Callable
from prompt_toolkit.layout.containers import HSplit, VSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.widgets import Box, Frame, Label, Button
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.application.current import get_app

from amadeus.providers import get_all_providers, get_cloud_providers, get_local_providers
from amadeus.i18n import get_translator
from .forms import NotificationDialog

# Configure logger
logger = logging.getLogger(__name__)


class ProviderCard:
    """Carte d'affichage pour un provider avec ses informations détaillées."""
    
    def __init__(self, provider_id: str, config: Dict[str, Any], 
                 on_configure: Callable = None, on_details: Callable = None):
        self.provider_id = provider_id
        self.config = config
        self.on_configure = on_configure
        self.on_details = on_details
        self.translator = get_translator()
    
    def create_card(self, width: int = 60) -> VSplit:
        """Crée une carte visuelle pour le provider."""
        name = self.config.get('name', self.provider_id)
        description = self.config.get('description', 'No description')
        provider_type = self.config.get('provider_type', 'unknown')
        is_configured = self.config.get('is_configured', False)
        is_available = self.config.get('is_available', False)
        version = self.config.get('version', 'Unknown')
        
        # Icônes selon le type et le statut
        type_icon = "☁️" if provider_type == "cloud" else "🏠"
        status_icon = "✅" if is_configured else "⚙️"
        availability_icon = "🟢" if is_available else "🔴"
        
        # Informations principales
        header = f"{type_icon} {name}"
        status_text = f"{status_icon} {'Configured' if is_configured else 'Not configured'}"
        availability_text = f"{availability_icon} {'Available' if is_available else 'Unavailable'}"
        
        # Contenu de la carte
        card_content = HSplit([
            Label(HTML(f"<info><b>{header}</b></info>")),
            Label(HTML(f"<secondary>{description}</secondary>")),
            Window(height=1),
            Label(HTML(f"<accent>Type:</accent> {provider_type.title()}")),
            Label(HTML(f"<accent>Version:</accent> {version}")),
            Label(HTML(f"<accent>Status:</accent> {status_text}")),
            Label(HTML(f"<accent>Availability:</accent> {availability_text}")),
            Window(height=1),
            self._create_action_buttons()
        ])
        
        # Frame avec bordure
        card_frame = Frame(
            card_content,
            title=f" {self.provider_id} ",
            style="class:provider-card"
        )
        
        return Box(
            card_frame,
            padding=1,
            width=Dimension(preferred=width),
            style="class:provider-card-container"
        )
    
    def _create_action_buttons(self) -> VSplit:
        """Crée les boutons d'action pour la carte."""
        buttons = []
        
        if self.on_configure:
            config_text = "🔧 Reconfigure" if self.config.get('is_configured') else "⚙️ Configure"
            buttons.append(Button(config_text, handler=lambda: self.on_configure(self.provider_id)))
        
        if self.on_details:
            buttons.append(Button("ℹ️ Details", handler=lambda: self.on_details(self.provider_id)))
        
        return VSplit(buttons, padding=1) if buttons else Window(height=1)


class ProviderListView:
    """Vue en liste pour afficher tous les providers avec filtres."""
    
    def __init__(self, on_configure: Callable = None, on_details: Callable = None):
        self.on_configure = on_configure
        self.on_details = on_details
        self.translator = get_translator()
        self.current_filter = "all"  # all, cloud, local, configured, unconfigured
        self.providers_data = {}
        self.kb = KeyBindings()
        
        # Navigation clavier
        @self.kb.add('f')
        def _(event):
            self._cycle_filter()
        
        @self.kb.add('r')
        def _(event):
            self._refresh_providers()
    
    def _refresh_providers(self):
        """Actualise la liste des providers."""
        try:
            from amadeus.providers import refresh_providers, force_database_sync
            
            # Forcer la redécouverte et la synchronisation
            refresh_providers()
            force_database_sync()
            
            logger.info("Providers refreshed and synchronized with database")
        except ImportError:
            # Si les nouvelles fonctions ne sont pas disponibles, essayer l'ancienne méthode
            try:
                from amadeus.providers import registry
                if hasattr(registry, '__init__'):
                    registry.__init__()
            except Exception as fallback_e:
                logger.error(f"Fallback refresh error: {fallback_e}")
        except Exception as e:
            logger.error(f"Error refreshing providers: {e}")
        
        # Recharger les données
        self.providers_data = get_all_providers()
        get_app().invalidate()
    
    def _cycle_filter(self):
        """Change le filtre actuel."""
        filters = ["all", "cloud", "local", "configured", "unconfigured"]
        current_index = filters.index(self.current_filter)
        self.current_filter = filters[(current_index + 1) % len(filters)]
        get_app().invalidate()
    
    def _filter_providers(self) -> Dict[str, Dict[str, Any]]:
        """Filtre les providers selon le filtre actuel."""
        if not self.providers_data:
            self.providers_data = get_all_providers()
        
        filtered = {}
        
        for provider_id, config in self.providers_data.items():
            include = True
            
            if self.current_filter == "cloud":
                include = config.get('provider_type') == 'cloud'
            elif self.current_filter == "local":
                include = config.get('provider_type') == 'local'
            elif self.current_filter == "configured":
                include = config.get('is_configured', False)
            elif self.current_filter == "unconfigured":
                include = not config.get('is_configured', False)
            
            if include:
                filtered[provider_id] = config
        
        return filtered
    
    def create_list_view(self, width: int = 80) -> HSplit:
        """Crée la vue en liste complète."""
        filtered_providers = self._filter_providers()
        
        # En-tête avec filtres et statistiques
        header = self._create_header(len(filtered_providers))
        
        # Liste des providers
        provider_cards = []
        for provider_id, config in filtered_providers.items():
            card = ProviderCard(
                provider_id, 
                config, 
                self.on_configure, 
                self.on_details
            )
            provider_cards.append(card.create_card(width - 10))
            provider_cards.append(Window(height=1))  # Espacement
        
        if not provider_cards:
            provider_cards = [
                Label(HTML(f"<warning>No providers found for filter: {self.current_filter}</warning>"))
            ]
        
        # Conteneur principal
        content = HSplit([
            header,
            Window(height=1),
            HSplit(provider_cards)
        ])
        
        return content, self.kb
    
    def _create_header(self, count: int) -> Frame:
        """Crée l'en-tête avec filtres et statistiques."""
        filter_display = self.current_filter.title()
        
        header_content = VSplit([
            Label(HTML(f"<info><b>Providers ({filter_display}): {count}</b></info>")),
            Label(HTML("<secondary>F: Filter • R: Refresh</secondary>"))
        ], align="justify")
        
        return Frame(
            header_content,
            title=" Provider Management ",
            style="class:provider-header"
        )


class ProviderConfigForm:
    """Formulaire spécialisé pour la configuration des providers."""
    
    def __init__(self, provider_id: str, provider_config: Dict[str, Any], 
                 existing_credentials: Dict[str, str], on_submit: Callable, on_cancel: Callable):
        self.provider_id = provider_id
        self.provider_config = provider_config
        self.existing_credentials = existing_credentials
        self.on_submit = on_submit
        self.on_cancel = on_cancel
        self.translator = get_translator()
        
        from .forms import Form
        self.form = Form(
            title=f"Configure {provider_config.get('name', provider_id)}",
            on_submit=self._handle_submit,
            on_cancel=self._handle_cancel,
            width=70
        )
        
        self._setup_form_fields()
    
    def _setup_form_fields(self):
        """Configure les champs du formulaire selon les exigences du provider."""
        auth_requirements = self.provider_config.get('auth_requirements', [])
        
        # Informations du provider
        self.form.add_field(
            name="_info",
            label="Provider Information",
            default=f"Type: {self.provider_config.get('provider_type', 'Unknown')}\n"
                   f"Version: {self.provider_config.get('version', 'Unknown')}\n"
                   f"Description: {self.provider_config.get('description', 'No description')}",
            required=False,
            description="Read-only information about this provider"
        )
        
        # Champs d'authentification
        for req in auth_requirements:
            key = req.get('key', '')
            name = req.get('name', key)
            description = req.get('description', '')
            is_secret = req.get('secret', True)
            is_required = req.get('required', True)
            
            # Valeur actuelle
            current_value = self.existing_credentials.get(key, '')
            
            # Description enrichie
            if current_value and is_secret:
                description += f" (Current: {'*' * min(len(current_value), 8)})"
            elif current_value:
                description += f" (Current: {current_value})"
            
            self.form.add_field(
                name=key,
                label=name,
                default=current_value,
                secret=is_secret,
                required=is_required,
                description=description
            )
    
    def _handle_submit(self, values: Dict[str, str]):
        """Gère la soumission du formulaire."""
        # Retirer le champ d'information
        if "_info" in values:
            del values["_info"]
        
        # Valider les champs requis
        auth_requirements = self.provider_config.get('auth_requirements', [])
        for req in auth_requirements:
            key = req.get('key', '')
            if req.get('required', True) and not values.get(key):
                # Afficher une erreur
                dialog = NotificationDialog(
                    title="Validation Error",
                    text=f"Field '{req.get('name', key)}' is required.",
                    buttons=[("OK", lambda: None)]
                )
                return
        
        self.on_submit(self.provider_id, values)
    
    def _handle_cancel(self):
        """Gère l'annulation du formulaire."""
        self.on_cancel()
    
    def create_form(self):
        """Crée le formulaire de configuration."""
        return self.form.create_form()
