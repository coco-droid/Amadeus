"""
Menu de gestion des providers pour Amadeus
"""

from amadeus.core.ui.components.forms import Form, NotificationDialog
from amadeus.providers import registry, config_manager, get_cloud_providers, get_local_providers
from amadeus.i18n import get_translator
import logging

# Utiliser le logger sans configuration supplémentaire
logger = logging.getLogger("providers_menu")

def show_providers_menu(app):
    """Affiche le menu des providers."""
    app.is_main_menu = False
    translator = get_translator()
    
    submenu_options = [
        (translator.get("add_update_provider"), lambda: manage_provider(app, "add")),
        (translator.get("list_configured_providers"), lambda: manage_provider(app, "list")),
        (translator.get("delete_provider"), lambda: manage_provider(app, "delete")),
        (translator.get("return"), lambda: app.show_main_menu())
    ]
    
    title = translator.get("provider_config")
    menu, kb = app.menu_manager.show_menu(title, submenu_options, width=40)
    app.show_menu_container(menu, kb)

def manage_provider(app, action):
    """Gère les opérations sur les providers."""
    translator = get_translator()
    
    if action == "add":
        # Options pour choisir entre providers cloud et locaux
        options = [
            (translator.get("cloud_providers"), lambda: select_cloud_provider(app)),
            (translator.get("local_providers"), lambda: select_local_provider(app)),
            (translator.get("return"), lambda: show_providers_menu(app))
        ]
        
        title = translator.get("provider_type")
        menu, kb = app.menu_manager.show_menu(title, options, width=40)
        app.show_menu_container(menu, kb)
        
    elif action == "list":
        list_configured_providers(app)
    elif action == "delete":
        delete_provider_menu(app)
    else:
        show_providers_menu(app)

def select_cloud_provider(app):
    """Affiche la liste des providers cloud disponibles."""
    translator = get_translator()
    
    # Récupérer les providers cloud
    cloud_providers = get_cloud_providers()
    logger.info(f"Providers cloud disponibles: {list(cloud_providers.keys())}")
    
    # Créer les options à partir des providers cloud disponibles
    options = []
    
    if not cloud_providers:
        options.append((f"❌ {translator.get('no_cloud_provider_found')}", lambda: None))
    else:
        for provider_id, config in cloud_providers.items():
            provider_name = config.get("name", provider_id)
            description = config.get("description", "")
            
            # Ajouter des icônes spécifiques selon le provider
            if "openai" in provider_id.lower():
                icon = "🤖"
            elif "anthropic" in provider_id.lower():
                icon = "🧠"
            elif "google" in provider_id.lower():
                icon = "🔍"
            elif "azure" in provider_id.lower():
                icon = "☁️"
            elif "aws" in provider_id.lower():
                icon = "🚀"
            else:
                icon = "⚡"
                
            options.append((
                f"{icon} {provider_name} - {description}",
                lambda pid=provider_id: configure_provider(app, pid)
            ))
    
    # Ajouter l'option de retour
    options.append((f"↩️ {translator.get('return')}", lambda: manage_provider(app, "add")))
    
    title = f"☁️ {translator.get('available_cloud_providers')}"
    menu, kb = app.menu_manager.show_menu(title, options, width=70)
    app.show_menu_container(menu, kb)

def select_local_provider(app):
    """Affiche la liste des providers locaux disponibles."""
    translator = get_translator()
    
    # Récupérer les providers locaux
    local_providers = get_local_providers()
    logger.info(f"Providers locaux disponibles: {list(local_providers.keys())}")
    
    # Créer les options à partir des providers locaux disponibles
    options = []
    
    if not local_providers:
        options.append((f"❌ {translator.get('no_local_provider_found')}", lambda: None))
    else:
        for provider_id, config in local_providers.items():
            provider_name = config.get("name", provider_id)
            description = config.get("description", "")
            
            # Ajouter des icônes spécifiques selon le provider
            if "ollama" in provider_id.lower():
                icon = "🦙"
            elif "llamacpp" in provider_id.lower():
                icon = "🦜"
            elif "vllm" in provider_id.lower():
                icon = "⚡"
            elif "huggingface" in provider_id.lower():
                icon = "🤗"
            else:
                icon = "🏠"
                
            options.append((
                f"{icon} {provider_name} - {description}",
                lambda pid=provider_id: configure_provider(app, pid)
            ))
    
    # Ajouter l'option de retour
    options.append((f"↩️ {translator.get('return')}", lambda: manage_provider(app, "add")))
    
    title = f"🏠 {translator.get('available_local_providers')}"
    menu, kb = app.menu_manager.show_menu(title, options, width=70)
    app.show_menu_container(menu, kb)

def configure_provider(app, provider_id):
    """Interface pour configurer un provider spécifique."""
    translator = get_translator()
    
    try:
        # Récupérer la configuration du provider
        provider_config = registry.get_provider_config(provider_id)
        logger.info(f"Configuration du provider {provider_id}: {provider_config}")
        
        # Récupérer les informations d'identification existantes si disponibles
        existing_credentials = config_manager.get_provider_config(provider_id) or {}
        
        # Récupérer les exigences d'authentification
        auth_requirements = provider_config.get("auth_requirements", [])
        
        title = f"{translator.get('provider_config')} {provider_config.get('name', provider_id)}"
        
        # Créer un formulaire pour saisir les informations d'identification
        form = Form(
            title=title, 
            on_submit=lambda values: save_provider_credentials(app, provider_id, values),
            on_cancel=lambda: select_provider_type(app, provider_id),
            width=60
        )
        
        # Ajouter un champ pour chaque exigence d'authentification
        for req in auth_requirements:
            key = req.get("key", "")
            name = req.get("name", key)
            description = req.get("description", "")
            is_secret = req.get("secret", True)
            is_required = req.get("required", True)
            
            # Valeur actuelle si disponible
            current_value = existing_credentials.get(key, "")
            
            form.add_field(
                name=key,
                label=name,
                default=current_value,
                secret=is_secret,
                required=is_required,
                description=description
            )
        
        # Afficher le formulaire
        form_container, form_kb = form.create_form()
        app.show_form_container(form_container, form_kb)
        
    except Exception as e:
        logger.error(f"Erreur lors de la configuration du provider {provider_id}: {e}", exc_info=True)
        title = translator.get("error")
        dialog = NotificationDialog(
            title=title,
            text=f"{translator.get('error')}: {str(e)}",
            buttons=[(translator.get("back"), lambda: manage_provider(app, "add"))]
        )
        dialog_container, dialog_kb = dialog.create_dialog()
        app.show_dialog_container(dialog_container, dialog_kb)

def select_provider_type(app, provider_id):
    """Détermine si le provider est local ou cloud et retourne au menu approprié."""
    if provider_id.startswith("cloud."):
        select_cloud_provider(app)
    elif provider_id.startswith("local."):
        select_local_provider(app)
    else:
        manage_provider(app, "add")

def save_provider_credentials(app, provider_id, values):
    """Sauvegarde les informations d'identification du provider."""
    translator = get_translator()
    
    try:
        # Vérifier les valeurs requises
        provider_config = registry.get_provider_config(provider_id)
        auth_requirements = provider_config.get("auth_requirements", [])
        
        # Vérifier si toutes les valeurs requises sont fournies
        for req in auth_requirements:
            if req.get("required", True) and not values.get(req.get("key", "")):
                raise ValueError(f"Le champ {req.get('name', req.get('key', ''))} est requis")
        
        # Sauvegarde des informations d'identification
        config_manager.save_provider_config(provider_id, values)
        logger.info(f"Credentials sauvegardées pour le provider {provider_id}")
        
        # Afficher un message de succès
        dialog = NotificationDialog(
            title=translator.get("configuration_successful"),
            text=f"{translator.get('configuration_saved')} {provider_config.get('name', provider_id)}",
            buttons=[(translator.get("ok"), lambda: show_providers_menu(app))]
        )
        dialog_container, dialog_kb = dialog.create_dialog()
        app.show_dialog_container(dialog_container, dialog_kb)
        
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde des credentials: {e}", exc_info=True)
        # Afficher un message d'erreur
        dialog = NotificationDialog(
            title=translator.get("error"),
            text=f"{translator.get('configuration_error')} {str(e)}",
            buttons=[(translator.get("try_again"), lambda: configure_provider(app, provider_id))]
        )
        dialog_container, dialog_kb = dialog.create_dialog()
        app.show_dialog_container(dialog_container, dialog_kb)

def list_configured_providers(app):
    """Liste les providers configurés."""
    translator = get_translator()
    
    # Obtenir la liste des providers configurés
    configured_provider_ids = config_manager.get_all_providers()
    logger.info(f"Providers configurés: {configured_provider_ids}")
    
    if not configured_provider_ids:
        # Pas de providers configurés
        dialog = NotificationDialog(
            title=translator.get("configured_providers"),
            text=translator.get("no_configured_providers"),
            buttons=[(translator.get("back"), lambda: show_providers_menu(app))]
        )
        dialog_container, dialog_kb = dialog.create_dialog()
        app.show_dialog_container(dialog_container, dialog_kb)
        return
    
    # Options pour afficher les détails des providers
    options = []
    for provider_id in configured_provider_ids:
        try:
            # Récupérer la configuration du provider si elle existe
            provider_config = registry.get_provider_config(provider_id)
            provider_name = provider_config.get("name", provider_id)
            provider_type = provider_config.get("provider_type", "").upper()
            
            # Ajouter l'option pour afficher les détails
            options.append((
                f"{provider_name} ({provider_type})",
                lambda pid=provider_id: show_provider_details(app, pid)
            ))
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des détails du provider {provider_id}: {e}", exc_info=True)
            # Provider non trouvé dans le registre
            options.append((
                f"{provider_id} ({translator.get('unavailable')})",
                lambda pid=provider_id: show_provider_unavailable(app, pid)
            ))
    
    # Ajouter l'option de retour
    options.append((translator.get("return"), lambda: show_providers_menu(app)))
    
    title = translator.get("configured_providers")
    menu, kb = app.menu_manager.show_menu(title, options, width=50)
    app.show_menu_container(menu, kb)

def show_provider_unavailable(app, provider_id):
    """Affiche un message d'erreur pour un provider non disponible."""
    translator = get_translator()
    
    dialog = NotificationDialog(
        title=translator.get("provider_unavailable"),
        text=f"{translator.get('provider_unavailable')} {provider_id}.\n"
             f"Vous pouvez supprimer sa configuration ou réinstaller le provider.",
        buttons=[
            (translator.get("delete_provider"), lambda: confirm_delete_provider(app, provider_id, provider_id)),
            (translator.get("back"), lambda: list_configured_providers(app))
        ]
    )
    dialog_container, dialog_kb = dialog.create_dialog()
    app.show_dialog_container(dialog_container, dialog_kb)

def show_provider_details(app, provider_id):
    """Affiche les détails d'un provider configuré."""
    translator = get_translator()
    
    try:
        # Récupérer les configurations
        provider_config = registry.get_provider_config(provider_id)
        credentials = config_manager.get_provider_config(provider_id)
        
        provider_name = provider_config.get("name", provider_id)
        provider_type = provider_config.get("provider_type", "unknown").upper()
        
        # Préparer les options pour afficher les détails
        options = [
            (f"{translator.get('type')} {provider_type}", lambda: None),
            (f"{translator.get('description')} {provider_config.get('description', translator.get('unavailable'))}", lambda: None)
        ]
        
        # Afficher les fonctionnalités
        features = provider_config.get("supported_features", {})
        feature_str = []
        for feature, value in features.items():
            if isinstance(value, bool):
                status = "✓" if value else "✗"
                feature_str.append(f"{feature}: {status}")
            elif isinstance(value, list):
                feature_str.append(f"{feature}: {', '.join(value)}")
        
        if feature_str:
            options.append((f"{translator.get('features')}:", lambda: None))
            for fs in feature_str:
                options.append((f"  {fs}", lambda: None))
        
        # Afficher les modèles par défaut
        default_models = provider_config.get("default_models", [])
        if default_models:
            options.append((f"{translator.get('default_models')}:", lambda: None))
            for model in default_models:
                model_id = model.get("id", "")
                model_name = model.get("name", model_id)
                options.append((f"  {model_name}", lambda: None))
        
        # Option pour reconfigurer le provider
        options.append((translator.get("reconfigure"), lambda: configure_provider(app, provider_id)))
        
        # Option de retour
        options.append((translator.get("return"), lambda: list_configured_providers(app)))
        
        title = f"{translator.get('details')} {provider_name}"
        menu, kb = app.menu_manager.show_menu(title, options, width=60)
        app.show_menu_container(menu, kb)
        
    except Exception as e:
        logger.error(f"Erreur lors de l'affichage des détails du provider {provider_id}: {e}", exc_info=True)
        # Provider non trouvé
        dialog = NotificationDialog(
            title=translator.get("error"),
            text=f"{translator.get('error')}: {str(e)}",
            buttons=[(translator.get("back"), lambda: list_configured_providers(app))]
        )
        dialog_container, dialog_kb = dialog.create_dialog()
        app.show_dialog_container(dialog_container, dialog_kb)

def delete_provider_menu(app):
    """Affiche le menu de suppression des providers."""
    translator = get_translator()
    
    # Obtenir la liste des providers configurés
    configured_provider_ids = config_manager.get_all_providers()
    logger.info(f"Providers disponibles pour suppression: {configured_provider_ids}")
    
    if not configured_provider_ids:
        # Pas de providers configurés
        dialog = NotificationDialog(
            title=translator.get("delete_provider"),
            text=translator.get("no_configured_providers"),
            buttons=[(translator.get("back"), lambda: show_providers_menu(app))]
        )
        dialog_container, dialog_kb = dialog.create_dialog()
        app.show_dialog_container(dialog_container, dialog_kb)
        return
    
    # Options pour supprimer les providers
    options = []
    for provider_id in configured_provider_ids:
        try:
            # Récupérer la configuration du provider si elle existe
            provider_config = registry.get_provider_config(provider_id)
            provider_name = provider_config.get("name", provider_id)
            
            # Ajouter l'option pour confirmer la suppression
            options.append((
                f"🗑️ {provider_name}",
                lambda pid=provider_id, pname=provider_name: confirm_delete_provider(app, pid, pname)
            ))
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du provider {provider_id} pour suppression: {e}", exc_info=True)
            # Provider non trouvé dans le registre
            options.append((
                f"🗑️ {provider_id} ({translator.get('unavailable')})",
                lambda pid=provider_id: confirm_delete_provider(app, pid, provider_id)
            ))
    
    # Ajouter l'option de retour
    options.append((translator.get("return"), lambda: show_providers_menu(app)))
    
    title = translator.get("delete_provider")
    menu, kb = app.menu_manager.show_menu(title, options, width=50)
    app.show_menu_container(menu, kb)

def confirm_delete_provider(app, provider_id, provider_name):
    """Demande confirmation avant de supprimer un provider."""
    translator = get_translator()
    
    # Créer le dialogue de confirmation
    dialog = NotificationDialog(
        title=translator.get("delete_confirmation"),
        text=f"{translator.get('delete_provider_confirm')} {provider_name} ?",
        buttons=[
            (translator.get("yes"), lambda: delete_provider(app, provider_id)),
            (translator.get("no"), lambda: delete_provider_menu(app))
        ]
    )
    dialog_container, dialog_kb = dialog.create_dialog()
    app.show_dialog_container(dialog_container, dialog_kb)

def delete_provider(app, provider_id):
    """Supprime un provider."""
    translator = get_translator()
    
    try:
        # Supprimer le provider
        success = config_manager.delete_provider_config(provider_id)
        logger.info(f"Suppression du provider {provider_id}: {'succès' if success else 'échec'}")
        
        if success:
            # Afficher un message de succès
            dialog = NotificationDialog(
                title=f"✅ {translator.get('deletion_successful')}",
                text=f"🗑️ {translator.get('provider_deleted')}",
                buttons=[(f"👍 {translator.get('ok')}", lambda: show_providers_menu(app))]
            )
        else:
            # Afficher un message d'erreur
            dialog = NotificationDialog(
                title=f"❌ {translator.get('error')}",
                text=f"⚠️ {translator.get('deletion_failed')}",
                buttons=[(f"🔙 {translator.get('back')}", lambda: delete_provider_menu(app))]
            )
        
        dialog_container, dialog_kb = dialog.create_dialog()
        app.show_dialog_container(dialog_container, dialog_kb)
        
    except Exception as e:
        logger.error(f"Erreur lors de la suppression du provider {provider_id}: {e}", exc_info=True)
        # Afficher un message d'erreur
        dialog = NotificationDialog(
            title=f"❌ {translator.get('error')}",
            text=f"⚠️ {translator.get('error')}: {str(e)}",
            buttons=[(f"🔙 {translator.get('back')}", lambda: delete_provider_menu(app))]
        )
        dialog_container, dialog_kb = dialog.create_dialog()
        app.show_dialog_container(dialog_container, dialog_kb)
