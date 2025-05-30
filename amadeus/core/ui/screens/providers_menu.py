"""
Menu de gestion des providers pour Amadeus
"""

import logging
from amadeus.core.ui.components.forms import Form, NotificationDialog
from amadeus.providers import (
    registry, config_manager, get_cloud_providers, get_local_providers,
    debug_provider_discovery, get_database_status, force_database_sync,
    rebuild_database, clear_database_providers, refresh_providers,
    get_all_providers
)
from amadeus.i18n import get_translator

# Configure logger
logger = logging.getLogger(__name__)

def show_providers_menu(app):
    """Affiche le menu des providers."""
    app.is_main_menu = False
    translator = get_translator()
    
    submenu_options = [
        (translator.get("add_update_provider"), lambda: manage_provider(app, "add")),
        (translator.get("list_configured_providers"), lambda: manage_provider(app, "list")),
        (translator.get("delete_provider"), lambda: manage_provider(app, "delete")),
        ("🔧 Debug Database", lambda: show_debug_menu(app)),
        (translator.get("return"), lambda: app.show_main_menu())
    ]
    
    title = translator.get("provider_config")
    menu, kb = app.menu_manager.show_menu(title, submenu_options, width=40)
    app.show_menu_container(menu, kb)

def show_debug_menu(app):
    """Affiche le menu de debug de la base de données."""
    translator = get_translator()
    
    # Vérifier l'état de la fenêtre debug
    from amadeus.core.debug_window import is_debug_enabled, enable_debug_window, disable_debug_window
    
    debug_status = "🟢 Activée" if is_debug_enabled() else "🔴 Désactivée"
    debug_action = "Désactiver" if is_debug_enabled() else "Activer"
    
    debug_options = [
        ("🔍 Debug Discovery", lambda: debug_and_show_status(app)),
        ("📋 List Discovered Providers", lambda: list_discovered_providers(app)),
        ("📊 Database Status", lambda: show_database_status(app)),
        ("🔄 Force DB Sync", lambda: force_sync_and_notify(app)),
        (f"🪟 Fenêtre Debug ({debug_status})", lambda: toggle_debug_window(app)),
        ("📝 Error Summary", lambda: show_error_summary(app)),
        ("🏗️ Rebuild Database", lambda: rebuild_database_and_notify(app)),
        ("🗑️ Clear Database", lambda: confirm_clear_database(app)),
        ("🔙 Back", lambda: show_providers_menu(app))
    ]
    
    title = "🔧 Provider Database Debug"
    menu, kb = app.menu_manager.show_menu(title, debug_options, width=50)
    app.show_menu_container(menu, kb)

def toggle_debug_window(app):
    """Active/désactive la fenêtre de debug."""
    from amadeus.core.debug_window import is_debug_enabled, enable_debug_window, disable_debug_window
    from amadeus.core.ui.components.forms import NotificationDialog
    
    if is_debug_enabled():
        disable_debug_window()
        message = "Fenêtre de debug désactivée."
        title = "🔴 Debug Désactivé"
    else:
        success = enable_debug_window()
        if success:
            message = "Fenêtre de debug activée!\nUne nouvelle fenêtre de terminal devrait s'ouvrir avec les logs en temps réel."
            title = "🟢 Debug Activé"
        else:
            message = "Erreur lors de l'activation de la fenêtre de debug."
            title = "❌ Erreur"
    
    dialog = NotificationDialog(
        title=title,
        text=message,
        buttons=[("🔙 Retour", lambda: show_debug_menu(app))]
    )
    dialog_container, dialog_kb = dialog.create_dialog()
    app.show_dialog_container(dialog_container, dialog_kb)

def show_error_summary(app):
    """Affiche un résumé des erreurs récentes."""
    try:
        from amadeus import get_error_summary
        from amadeus.core.logging.log_manager import LogManager
        
        # Récupérer les erreurs en mémoire
        memory_summary = get_error_summary()
        
        # Récupérer les erreurs des fichiers logs
        log_manager = LogManager()
        file_summary = log_manager.get_error_summary()
        
        lines = [
            "=== 📝 RÉSUMÉ DES ERREURS ===",
            "",
            "📋 Erreurs en mémoire (session actuelle):",
            f"  Erreurs: {memory_summary['total_errors']}",
            f"  Warnings: {memory_summary['total_warnings']}",
            "",
            "📁 Erreurs dans les fichiers logs:",
            f"  Erreurs: {file_summary['total_errors']}",
            f"  Warnings: {file_summary['total_warnings']}",
            "",
        ]
        
        if memory_summary['errors']:
            lines.append("🔴 Erreurs récentes (mémoire):")
            for error in memory_summary['errors'][-5:]:  # 5 plus récentes
                lines.append(f"  • {error}")
            lines.append("")
        
        if file_summary['recent_errors']:
            lines.append("🔴 Erreurs récentes (fichiers):")
            for error in file_summary['recent_errors'][:5]:  # 5 plus récentes
                lines.append(f"  • {error['message']}")
            lines.append("")
        
        if not memory_summary['errors'] and not file_summary['recent_errors']:
            lines.append("✅ Aucune erreur récente trouvée!")
        
        error_text = "\n".join(lines)
        
        dialog = NotificationDialog(
            title="📝 Résumé des Erreurs",
            text=error_text,
            buttons=[
                ("🔄 Actualiser", lambda: show_error_summary(app)),
                ("🔙 Retour", lambda: show_debug_menu(app))
            ]
        )
        dialog_container, dialog_kb = dialog.create_dialog()
        app.show_dialog_container(dialog_container, dialog_kb)
        
    except Exception as e:
        logger.error(f"Erreur lors de l'affichage du résumé: {e}")
        
        dialog = NotificationDialog(
            title="❌ Erreur",
            text=f"Erreur lors de la génération du résumé: {str(e)}",
            buttons=[("🔙 Retour", lambda: show_debug_menu(app))]
        )
        dialog_container, dialog_kb = dialog.create_dialog()
        app.show_dialog_container(dialog_container, dialog_kb)

def debug_and_show_status(app):
    """Exécute le debug et affiche le statut."""
    try:
        # Exécuter le debug complet
        debug_provider_discovery()
        
        # Récupérer le statut
        status = get_database_status()
        
        # Préparer le message de statut
        status_text = f"""Debug completed! Check console for details.

Database Status:
• Registry: {status.get('total_in_registry', 0)} providers
• Database: {status.get('total_in_database', 0)} providers
• Synchronized: {len(status.get('synchronized', []))} providers

Registry only: {', '.join(status.get('in_registry_only', ['None']))}
Database only: {', '.join(status.get('in_database_only', ['None']))}"""
        
        # Afficher dans un dialogue
        dialog = NotificationDialog(
            title="🔍 Debug Results",
            text=status_text,
            buttons=[
                ("📊 Full Status", lambda: show_database_status(app)),
                ("🔙 Back", lambda: show_debug_menu(app))
            ]
        )
        dialog_container, dialog_kb = dialog.create_dialog()
        app.show_dialog_container(dialog_container, dialog_kb)
        
    except Exception as e:
        logger.error(f"Erreur pendant le debug: {e}")
        
        dialog = NotificationDialog(
            title="❌ Debug Error",
            text=f"Error during debug: {str(e)}",
            buttons=[("🔙 Back", lambda: show_debug_menu(app))]
        )
        dialog_container, dialog_kb = dialog.create_dialog()
        app.show_dialog_container(dialog_container, dialog_kb)

def show_database_status(app):
    """Affiche le statut détaillé de la base de données."""
    try:
        status = get_database_status()
        
        if 'error' in status:
            status_text = f"Database Error: {status['error']}"
        else:
            # Construire le texte de statut détaillé
            lines = [
                f"Registry Providers: {status.get('total_in_registry', 0)}",
                f"Database Providers: {status.get('total_in_database', 0)}",
                f"Synchronized: {len(status.get('synchronized', []))}",
                "",
                "Database Providers:"
            ]
            
            for provider in status.get('database_providers', []):
                status_icons = []
                if provider['available']:
                    status_icons.append("🟢")
                else:
                    status_icons.append("🔴")
                if provider['configured']:
                    status_icons.append("⚙️")
                else:
                    status_icons.append("❌")
                
                lines.append(f"  {''.join(status_icons)} {provider['provider_id']}")
                lines.append(f"    {provider['name']} ({provider['type']})")
            
            if not status.get('database_providers'):
                lines.append("  (No providers in database)")
            
            status_text = "\n".join(lines)
        
        # Afficher dans un dialogue scrollable
        dialog = NotificationDialog(
            title="📊 Database Status",
            text=status_text,
            buttons=[
                ("🔄 Refresh", lambda: show_database_status(app)),
                ("🔙 Back", lambda: show_debug_menu(app))
            ]
        )
        dialog_container, dialog_kb = dialog.create_dialog()
        app.show_dialog_container(dialog_container, dialog_kb)
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du statut: {e}")
        
        dialog = NotificationDialog(
            title="❌ Status Error",
            text=f"Error getting database status: {str(e)}",
            buttons=[("🔙 Back", lambda: show_debug_menu(app))]
        )
        dialog_container, dialog_kb = dialog.create_dialog()
        app.show_dialog_container(dialog_container, dialog_kb)

def force_sync_and_notify(app):
    """Force la synchronisation et affiche le résultat."""
    try:
        # Forcer la synchronisation
        force_database_sync()
        
        # Récupérer le nouveau statut
        status = get_database_status()
        
        result_text = f"""Synchronization completed!

Result:
• Registry: {status.get('total_in_registry', 0)} providers
• Database: {status.get('total_in_database', 0)} providers
• Synchronized: {len(status.get('synchronized', []))} providers"""
        
        dialog = NotificationDialog(
            title="✅ Sync Complete",
            text=result_text,
            buttons=[
                ("📊 View Status", lambda: show_database_status(app)),
                ("🔙 Back", lambda: show_debug_menu(app))
            ]
        )
        dialog_container, dialog_kb = dialog.create_dialog()
        app.show_dialog_container(dialog_container, dialog_kb)
        
    except Exception as e:
        logger.error(f"Erreur lors de la synchronisation: {e}")
        
        dialog = NotificationDialog(
            title="❌ Sync Error",
            text=f"Error during synchronization: {str(e)}",
            buttons=[("🔙 Back", lambda: show_debug_menu(app))]
        )
        dialog_container, dialog_kb = dialog.create_dialog()
        app.show_dialog_container(dialog_container, dialog_kb)

def rebuild_database_and_notify(app):
    """Reconstruit la base de données et affiche le résultat."""
    # Demander confirmation d'abord
    dialog = NotificationDialog(
        title="⚠️ Rebuild Database",
        text="This will delete all provider configurations and rebuild the database from scratch.\n\nAre you sure?",
        buttons=[
            ("✅ Yes, Rebuild", lambda: do_rebuild_database(app)),
            ("❌ Cancel", lambda: show_debug_menu(app))
        ]
    )
    dialog_container, dialog_kb = dialog.create_dialog()
    app.show_dialog_container(dialog_container, dialog_kb)

def do_rebuild_database(app):
    """Exécute la reconstruction de la base de données."""
    try:
        # Exécuter la reconstruction
        result = rebuild_database()
        
        if 'error' in result:
            result_text = f"Rebuild failed: {result['error']}"
            title = "❌ Rebuild Failed"
        else:
            result_text = f"""Database rebuilt successfully!

Result:
• Registry: {result.get('total_in_registry', 0)} providers
• Database: {result.get('total_in_database', 0)} providers
• Synchronized: {len(result.get('synchronized', []))} providers

All provider configurations have been cleared.
You will need to reconfigure your providers."""
            title = "✅ Rebuild Complete"
        
        dialog = NotificationDialog(
            title=title,
            text=result_text,
            buttons=[
                ("📊 View Status", lambda: show_database_status(app)),
                ("🔙 Back", lambda: show_debug_menu(app))
            ]
        )
        dialog_container, dialog_kb = dialog.create_dialog()
        app.show_dialog_container(dialog_container, dialog_kb)
        
    except Exception as e:
        logger.error(f"Erreur lors de la reconstruction: {e}")
        
        dialog = NotificationDialog(
            title="❌ Rebuild Error",
            text=f"Error during database rebuild: {str(e)}",
            buttons=[("🔙 Back", lambda: show_debug_menu(app))]
        )
        dialog_container, dialog_kb = dialog.create_dialog()
        app.show_dialog_container(dialog_container, dialog_kb)

def confirm_clear_database(app):
    """Demande confirmation avant de vider la base de données."""
    dialog = NotificationDialog(
        title="⚠️ Clear Database",
        text="This will delete ALL providers and credentials from the database.\n\nThis action cannot be undone!\n\nAre you sure?",
        buttons=[
            ("🗑️ Yes, Clear All", lambda: do_clear_database(app)),
            ("❌ Cancel", lambda: show_debug_menu(app))
        ]
    )
    dialog_container, dialog_kb = dialog.create_dialog()
    app.show_dialog_container(dialog_container, dialog_kb)

def do_clear_database(app):
    """Exécute la suppression de tous les providers de la DB."""
    try:
        # Exécuter la suppression
        result = clear_database_providers()
        
        if 'error' in result:
            result_text = f"Clear failed: {result['error']}"
            title = "❌ Clear Failed"
        else:
            result_text = f"""Database cleared successfully!

Deleted:
• {result.get('deleted_providers', 0)} providers
• {result.get('deleted_credentials', 0)} credentials

The database is now empty."""
            title = "✅ Database Cleared"
        
        dialog = NotificationDialog(
            title=title,
            text=result_text,
            buttons=[
                ("📊 View Status", lambda: show_database_status(app)),
                ("🔙 Back", lambda: show_debug_menu(app))
            ]
        )
        dialog_container, dialog_kb = dialog.create_dialog()
        app.show_dialog_container(dialog_container, dialog_kb)
        
    except Exception as e:
        logger.error(f"Erreur lors de la suppression: {e}")
        
        dialog = NotificationDialog(
            title="❌ Clear Error",
            text=f"Error clearing database: {str(e)}",
            buttons=[("🔙 Back", lambda: show_debug_menu(app))]
        )
        dialog_container, dialog_kb = dialog.create_dialog()
        app.show_dialog_container(dialog_container, dialog_kb)

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
    
    logger.info("=== DÉBUT select_cloud_provider ===")
    
    # Force refresh des providers avec nouveau registry robuste
    try:
        logger.info("Redécouverte des providers avec registry amélioré...")
        from amadeus.providers.registry import ProviderRegistry
        
        # Créer une nouvelle instance pour forcer la redécouverte
        new_registry = ProviderRegistry()
        
        # Obtenir le statut de découverte
        discovery_status = new_registry.get_discovery_status()
        logger.info(f"Statut de découverte: {discovery_status}")
        
        # Mettre à jour le registry global
        global registry
        registry = new_registry
        
    except Exception as e:
        logger.error(f"Erreur lors de la redécouverte: {e}")
        logger.error(traceback.format_exc())
    
    # Récupérer les providers cloud
    cloud_providers = get_cloud_providers()
    logger.info(f"Providers cloud disponibles: {list(cloud_providers.keys())}")
    
    # Debug supplémentaire: vérifier tous les providers
    try:
        all_providers = get_all_providers()
        logger.info(f"Tous les providers disponibles: {list(all_providers.keys())}")
        for pid, pconfig in all_providers.items():
            logger.info(f"  {pid}: type={pconfig.get('provider_type')}, configured={pconfig.get('is_configured')}")
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de tous les providers: {e}")
    
    # Créer les options à partir des providers cloud disponibles
    options = []
    
    if not cloud_providers:
        # Ajouter une option de debug
        options.append((f"🔍 {translator.get('debug_discovery', 'Debug Discovery')}", lambda: debug_and_retry(app)))
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
            elif "google" in provider_id.lower() or "ai_studio" in provider_id.lower():
                icon = "🔍"
            elif "azure" in provider_id.lower():
                icon = "☁️"
            elif "aws" in provider_id.lower():
                icon = "🚀"
            else:
                icon = "⚡"
            
            # BUGFIX: Créer une fonction séparée pour éviter les problèmes de closure
            def create_configure_callback(pid):
                def callback():
                    configure_provider(app, pid)
                return callback
                
            options.append((
                f"{icon} {provider_name} - {description}",
                create_configure_callback(provider_id)
            ))
            
            logger.debug(f"Ajouté option pour provider {provider_id}: {provider_name}")
    
    # Ajouter l'option de retour
    options.append((f"↩️ {translator.get('return')}", lambda: manage_provider(app, "add")))
    
    title = f"☁️ {translator.get('available_cloud_providers')}"
    logger.info(f"Affichage du menu avec {len(options)} options")
    
    # IMPORTANT: S'assurer que le menu s'affiche correctement
    app.is_main_menu = False
    menu, kb = app.menu_manager.show_menu(title, options, width=70)
    app.show_menu_container(menu, kb)
    
    logger.info("=== FIN select_cloud_provider ===")

def debug_and_retry(app):
    """Fonction de debug et retry pour diagnostiquer les problèmes de discovery."""
    translator = get_translator()
    
    try:
        # Exécuter un debug complet
        debug_provider_discovery()
        
        # Afficher les résultats dans un dialogue
        from amadeus.core.ui.components.forms import NotificationDialog
        dialog = NotificationDialog(
            title="🔍 Debug Information",
            text="Debug information has been logged. Check the console for details.",
            buttons=[
                ("🔄 Retry", lambda: select_cloud_provider(app)),
                ("🔙 Back", lambda: manage_provider(app, "add"))
            ]
        )
        dialog_container, dialog_kb = dialog.create_dialog()
        app.show_dialog_container(dialog_container, dialog_kb)
        
    except Exception as e:
        logger.error(f"Erreur pendant le debug: {e}")
        select_cloud_provider(app)

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
            
            # BUGFIX: Créer une fonction séparée pour éviter les problèmes de closure
            def create_configure_callback(pid):
                def callback():
                    configure_provider(app, pid)
                return callback
                
            options.append((
                f"{icon} {provider_name} - {description}",
                create_configure_callback(provider_id)
            ))
    
    # Ajouter l'option de retour
    options.append((f"↩️ {translator.get('return')}", lambda: manage_provider(app, "add")))
    
    title = f"🏠 {translator.get('available_local_providers')}"
    menu, kb = app.menu_manager.show_menu(title, options, width=70)
    app.show_menu_container(menu, kb)

def configure_provider(app, provider_id):
    """Interface pour configurer un provider spécifique."""
    translator = get_translator()
    
    logger.info(f"=== DEBUT configure_provider pour {provider_id} ===")
    
    try:
        # Récupérer la configuration du provider depuis les providers cloud et locaux
        provider_config = None
        
        # Essayer d'abord les providers cloud
        cloud_providers = get_cloud_providers()
        if provider_id in cloud_providers:
            provider_config = cloud_providers[provider_id]
            logger.info(f"Provider cloud trouvé: {provider_id}")
        
        # Si pas trouvé, essayer les providers locaux
        if not provider_config:
            local_providers = get_local_providers()
            if provider_id in local_providers:
                provider_config = local_providers[provider_id]
                logger.info(f"Provider local trouvé: {provider_id}")
        
        # Si toujours pas trouvé, essayer le registry
        if not provider_config:
            provider_config = registry.get_provider_config(provider_id)
            logger.info(f"Provider registry trouvé: {provider_id}")
        
        if not provider_config:
            raise ValueError(f"Configuration du provider {provider_id} non trouvée")
        
        logger.info(f"Configuration du provider {provider_id}: {provider_config}")
        
        # S'assurer que le provider existe dans la base de données
        provider_name = provider_config.get("name", provider_id)
        provider_type = provider_config.get("provider_type", "cloud")
        
        logger.debug(f"Ensuring provider exists: {provider_id}, {provider_name}, {provider_type}")
        config_manager.ensure_provider_exists(provider_id, provider_name, provider_type)
        
        # Récupérer les informations d'identification existantes depuis le vault
        existing_credentials = config_manager.get_provider_config(provider_id) or {}
        logger.info(f"Credentials existantes pour {provider_id}: {list(existing_credentials.keys())}")
        
        # Récupérer les exigences d'authentification
        auth_requirements = provider_config.get("auth_requirements", [])
        logger.info(f"Auth requirements pour {provider_id}: {auth_requirements}")
        
        if not auth_requirements:
            # Si aucune authentification requise, afficher un message et continuer
            logger.warning(f"Aucune exigence d'authentification pour {provider_id}")
            dialog = NotificationDialog(
                title=translator.get("configuration_info"),
                text=f"Le provider {provider_config.get('name', provider_id)} ne nécessite pas de configuration d'authentification.",
                buttons=[
                    (translator.get("save_anyway"), lambda: save_provider_credentials(app, provider_id, {})),
                    (translator.get("back"), lambda: select_provider_type_safely(app, provider_id))
                ]
            )
            dialog_container, dialog_kb = dialog.create_dialog()
            app.show_dialog_container(dialog_container, dialog_kb)
            return
        
        # Titre avec indication si c'est une modification ou une nouvelle configuration
        action_text = translator.get("modify_configuration") if existing_credentials else translator.get("new_configuration")
        title = f"{action_text} - {provider_config.get('name', provider_id)}"
        
        logger.info(f"Création du formulaire: {title}")
        
        # Créer un formulaire pour saisir les informations d'identification
        form = Form(
            title=title, 
            on_submit=lambda values: save_provider_credentials(app, provider_id, values),
            on_cancel=lambda: select_provider_type_safely(app, provider_id),
            width=60
        )
        
        # Ajouter un champ pour chaque exigence d'authentification
        fields_added = 0
        for req in auth_requirements:
            key = req.get("key", "")
            name = req.get("name", key)
            description = req.get("description", "")
            is_secret = req.get("secret", True)
            is_required = req.get("required", True)
            
            # Valeur actuelle depuis le vault si disponible
            current_value = existing_credentials.get(key, "")
            
            # Si une valeur existe et que c'est un champ secret, afficher un indicateur
            if current_value and is_secret:
                description += f" (Valeur actuelle: {'*' * min(len(current_value), 8)})"
            elif current_value and not is_secret:
                description += f" (Valeur actuelle: {current_value})"
            
            logger.info(f"Ajout du champ: {key} - {name} (required: {is_required}, secret: {is_secret}, has_value: {bool(current_value)})")
            
            form.add_field(
                name=key,
                label=name,
                default=current_value,
                secret=is_secret,
                required=is_required,
                description=description
            )
            fields_added += 1
        
        # Vérifier qu'au moins un champ a été ajouté
        if fields_added == 0:
            raise ValueError("Aucun champ d'authentification trouvé dans la configuration")
        
        logger.info(f"Formulaire créé avec {fields_added} champs")
        
        # IMPORTANT: S'assurer que l'état du menu est correct
        app.is_main_menu = False
        
        # Afficher le formulaire
        form_container, form_kb = form.create_form()
        app.show_form_container(form_container, form_kb)
        
        logger.info("=== FIN configure_provider ===")
        
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

def select_provider_type_safely(app, provider_id):
    """Version sécurisée de select_provider_type avec logs."""
    logger.debug(f"select_provider_type_safely appelé pour {provider_id}")
    
    if provider_id.startswith("cloud."):
        logger.debug(f"Redirection vers cloud providers pour {provider_id}")
        select_cloud_provider(app)
    elif provider_id.startswith("local."):
        logger.debug(f"Redirection vers local providers pour {provider_id}")
        select_local_provider(app)
    else:
        logger.debug(f"Retour au menu add pour {provider_id}")
        manage_provider(app, "add")

def save_provider_credentials(app, provider_id, values):
    """Sauvegarde les informations d'identification du provider."""
    translator = get_translator()
    
    try:
        # Récupérer la configuration du provider pour validation
        provider_config = None
        
        # Essayer les providers cloud d'abord
        cloud_providers = get_cloud_providers()
        if provider_id in cloud_providers:
            provider_config = cloud_providers[provider_id]
        
        # Si pas trouvé, essayer les providers locaux
        if not provider_config:
            local_providers = get_local_providers()
            if provider_id in local_providers:
                provider_config = local_providers[provider_id]
        
        # Si toujours pas trouvé, essayer le registry
        if not provider_config:
            provider_config = registry.get_provider_config(provider_id)
        
        if not provider_config:
            raise ValueError(f"Configuration du provider {provider_id} non trouvée")
            
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
            
            # BUGFIX: Créer une fonction séparée pour éviter les problèmes de closure
            def create_details_callback(pid):
                def callback():
                    show_provider_details(app, pid)
                return callback
            
            # Ajouter l'option pour afficher les détails
            options.append((
                f"{provider_name} ({provider_type})",
                create_details_callback(provider_id)
            ))
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des détails du provider {provider_id}: {e}", exc_info=True)
            
            # BUGFIX: Créer une fonction séparée pour éviter les problèmes de closure
            def create_unavailable_callback(pid):
                def callback():
                    show_provider_unavailable(app, pid)
                return callback
            
            # Provider non trouvé dans le registre
            options.append((
                f"{provider_id} ({translator.get('unavailable')})",
                create_unavailable_callback(provider_id)
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
            
            # BUGFIX: Créer une fonction séparée pour éviter les problèmes de closure
            def create_delete_callback(pid, pname):
                def callback():
                    confirm_delete_provider(app, pid, pname)
                return callback
            
            # Ajouter l'option pour confirmer la suppression
            options.append((
                f"🗑️ {provider_name}",
                create_delete_callback(provider_id, provider_name)
            ))
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du provider {provider_id} pour suppression: {e}", exc_info=True)
            
            # BUGFIX: Créer une fonction séparée pour éviter les problèmes de closure
            def create_delete_unavailable_callback(pid):
                def callback():
                    confirm_delete_provider(app, pid, provider_id)
                return callback
            
            # Provider non trouvé dans le registre
            options.append((
                f"🗑️ {provider_id} ({translator.get('unavailable')})",
                create_delete_unavailable_callback(provider_id)
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

def list_discovered_providers(app):
    """Liste tous les providers découverts par le registry avec détails complets."""
    try:
        # Force refresh first
        refresh_providers()
        
        # Execute full debug discovery
        debug_provider_discovery()
        
        # Get all providers from registry
        all_providers = registry.get_all_providers()
        cloud_providers = registry.get_cloud_providers() 
        local_providers = registry.get_local_providers()
        
        # Get database status
        db_status = get_database_status()
        
        # Prepare detailed status text
        lines = [
            "=== 🔍 DISCOVERY SCAN RESULTS ===",
            f"📊 Total discovered: {len(all_providers)}",
            f"☁️  Cloud providers: {len(cloud_providers)}", 
            f"🏠 Local providers: {len(local_providers)}",
            "",
            "=== 🗃️ DATABASE SYNC STATUS ===",
        ]
        
        if 'error' in db_status:
            lines.append(f"❌ Database error: {db_status['error']}")
        else:
            lines.extend([
                f"📊 Total in database: {db_status.get('total_in_database', 0)}",
                f"🔄 Synchronized: {len(db_status.get('synchronized', []))}",
                f"➕ New (registry only): {db_status.get('in_registry_only', [])}",
                f"❓ Missing (DB only): {db_status.get('in_database_only', [])}",
            ])
        
        lines.append("")
        lines.append("=== 📁 DIRECTORY SCAN ===")
        
        # Check directories and files
        import os
        from pathlib import Path
        
        providers_path = Path(__file__).parent.parent.parent.parent / 'providers'
        lines.append(f"📂 Base path: {providers_path}")
        lines.append(f"📂 Exists: {providers_path.exists()}")
        
        if providers_path.exists():
            for provider_type in ['cloud', 'local']:
                type_path = providers_path / provider_type
                lines.append(f"")
                lines.append(f"📁 {provider_type.upper()} directory:")
                lines.append(f"  📂 Path: {type_path}")
                lines.append(f"  ✅ Exists: {type_path.exists()}")
                
                if type_path.exists():
                    try:
                        subdirs = [item for item in type_path.iterdir() if item.is_dir() and not item.name.startswith('__')]
                        lines.append(f"  📋 Subdirs: {[d.name for d in subdirs]}")
                        
                        # Check each subdirectory for config files
                        for subdir in subdirs:
                            config_file = subdir / "config.json"
                            lines.append(f"    📁 {subdir.name}/")
                            lines.append(f"      📄 config.json: {'✅' if config_file.exists() else '❌'}")
                            
                            if config_file.exists():
                                try:
                                    with open(config_file, 'r', encoding='utf-8') as f:
                                        config = json.load(f)
                                    
                                    provider_id = config.get('id', '❌ MISSING')
                                    provider_name = config.get('name', '❌ MISSING')
                                    lines.append(f"        🆔 ID: {provider_id}")
                                    lines.append(f"        📛 Name: {provider_name}")
                                    
                                    # Check if this provider was discovered
                                    if provider_id in all_providers:
                                        lines.append(f"        🔍 Status: ✅ DISCOVERED")
                                    else:
                                        lines.append(f"        🔍 Status: ❌ NOT DISCOVERED")
                                        
                                except Exception as e:
                                    lines.append(f"        ❌ Config error: {e}")
                                    
                    except Exception as e:
                        lines.append(f"  ❌ Error reading directory: {e}")
        
        lines.append("")
        lines.append("=== 🔹 DISCOVERED PROVIDERS DETAILS ===")
        
        if not all_providers:
            lines.append("❌ NO PROVIDERS WERE DISCOVERED!")
            lines.append("Check the directory structure and config files above.")
        else:
            for provider_id, config in all_providers.items():
                lines.append(f"")
                lines.append(f"🔹 {provider_id}")
                lines.append(f"  📛 Name: {config.get('name', 'N/A')}")
                lines.append(f"  🏷️  Type: {config.get('provider_type', 'N/A')}")
                lines.append(f"  ✅ Available: {config.get('is_available', 'N/A')}")
                lines.append(f"  📄 Config: {config.get('config_file', 'N/A')}")
                
                # Show database status for this provider
                if provider_id in db_status.get('synchronized', []):
                    lines.append(f"  🗃️  DB Status: ✅ SYNCHRONIZED")
                elif provider_id in db_status.get('in_registry_only', []):
                    lines.append(f"  🗃️  DB Status: ➕ NEEDS SYNC TO DB")
                elif provider_id in db_status.get('in_database_only', []):
                    lines.append(f"  🗃️  DB Status: ❓ IN DB BUT NOT DISCOVERED")
                else:
                    lines.append(f"  🗃️  DB Status: ❌ UNKNOWN")
                
                # Show auth requirements if any
                auth_reqs = config.get('auth_requirements', [])
                if auth_reqs:
                    auth_keys = [req.get('key', 'NO_KEY') for req in auth_reqs]
                    lines.append(f"  🔑 Auth fields: {auth_keys}")
        
        # Add sync recommendation
        lines.append("")
        lines.append("=== 🔧 RECOMMENDATIONS ===")
        if not all_providers:
            lines.append("1. Check if config.json files exist in provider subdirectories")
            lines.append("2. Verify JSON syntax in config files")
            lines.append("3. Check file permissions")
        elif db_status.get('in_registry_only'):
            lines.append("1. Run 'Force DB Sync' to add new providers to database")
        elif db_status.get('in_database_only'):
            lines.append("1. Some providers are in DB but not discovered")
            lines.append("2. They may have been deleted or moved")
        else:
            lines.append("✅ All systems operational!")
        
        status_text = "\n".join(lines)
        
        # Show in scrollable dialog
        dialog = NotificationDialog(
            title="🔍 Provider Discovery & Sync Report",
            text=status_text,
            buttons=[
                ("🔄 Refresh Scan", lambda: list_discovered_providers(app)),
                ("💾 Force DB Sync", lambda: force_sync_and_show_results(app)),
                ("🔙 Back", lambda: show_debug_menu(app))
            ]
        )
        dialog_container, dialog_kb = dialog.create_dialog()
        app.show_dialog_container(dialog_container, dialog_kb)
        
    except Exception as e:
        logger.error(f"Error in discovery scan: {e}")
        
        dialog = NotificationDialog(
            title="❌ Discovery Error", 
            text=f"Error during discovery scan:\n{str(e)}\n\nCheck console for details.",
            buttons=[("🔙 Back", lambda: show_debug_menu(app))]
        )
        dialog_container, dialog_kb = dialog.create_dialog()
        app.show_dialog_container(dialog_container, dialog_kb)

def force_sync_and_show_results(app):
    """Force sync and show detailed results."""
    try:
        # Get status before sync
        before_status = get_database_status()
        before_total = before_status.get('total_in_database', 0)
        
        # Force the synchronization
        force_database_sync()
        
        # Get status after sync
        after_status = get_database_status()
        after_total = after_status.get('total_in_database', 0)
        
        # Prepare results
        lines = [
            "=== 💾 SYNC RESULTS ===",
            f"Before sync: {before_total} providers in DB",
            f"After sync:  {after_total} providers in DB",
            f"Added:       {after_total - before_total} providers",
            "",
            "=== 📊 CURRENT STATUS ===",
            f"Registry:     {after_status.get('total_in_registry', 0)} providers",
            f"Database:     {after_total} providers", 
            f"Synchronized: {len(after_status.get('synchronized', []))} providers",
            "",
        ]
        
        if after_status.get('synchronized'):
            lines.append("✅ Synchronized providers:")
            for provider_id in after_status.get('synchronized', []):
                lines.append(f"  🔹 {provider_id}")
        
        if after_status.get('in_registry_only'):
            lines.append("")
            lines.append("⚠️ Still not in database:")
            for provider_id in after_status.get('in_registry_only', []):
                lines.append(f"  ❓ {provider_id}")
        
        result_text = "\n".join(lines)
        
        dialog = NotificationDialog(
            title="💾 Sync Complete",
            text=result_text,
            buttons=[
                ("🔍 View Full Report", lambda: list_discovered_providers(app)),
                ("🔙 Back to Debug", lambda: show_debug_menu(app))
            ]
        )
        dialog_container, dialog_kb = dialog.create_dialog()
        app.show_dialog_container(dialog_container, dialog_kb)
        
    except Exception as e:
        logger.error(f"Error during sync: {e}")
        
        dialog = NotificationDialog(
            title="❌ Sync Error",
            text=f"Error during synchronization:\n{str(e)}",
            buttons=[("🔙 Back", lambda: show_debug_menu(app))]
        )
        dialog_container, dialog_kb = dialog.create_dialog()
        app.show_dialog_container(dialog_container, dialog_kb)
