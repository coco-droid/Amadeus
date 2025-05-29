"""
Menu principal de l'application Amadeus.
"""
from prompt_toolkit.application.current import get_app

from amadeus.i18n import get_translator
from amadeus.core.ui.screens.providers_menu import show_providers_menu

def show_initial_language_selection(app):
    """Affiche la sélection de langue au démarrage de l'application."""
    import logging
    logger = logging.getLogger("amadeus.ui.screens.main_menu")
    
    logger.info("Affichage de la sélection de langue initiale")
    app.is_main_menu = False
    
    # Options de langue avec callbacks qui changent la langue et passent au menu principal
    language_options = [
        ("🇬🇧 English", lambda: (app.change_language("en"), show_main_menu(app))[1]),
        ("🇫🇷 Français", lambda: (app.change_language("fr"), show_main_menu(app))[1]),
    ]
    
    logger.info(f"Options de langue créées: {len(language_options)} options")
    
    # Utiliser une clé de traduction neutre ou un titre statique
    title = "Language Selection / Sélection de la langue"
    
    try:
        menu, kb = app.menu_manager.show_menu(title, language_options, width=40)
        logger.info("Menu de sélection de langue créé avec succès")
        app.show_menu_container(menu, kb)
        logger.info("Menu de sélection de langue affiché")
    except Exception as e:
        logger.error(f"Erreur lors de la création/affichage du menu de langue: {e}")
        logger.exception("Détails de l'erreur:")
        # Fallback : aller directement au menu principal en anglais
        app.change_language("en")
        show_main_menu(app)

def show_main_menu(app):
    """Affiche le menu principal de l'application."""
    import logging
    logger = logging.getLogger("amadeus.ui.screens.main_menu")
    
    logger.info("Affichage du menu principal")
    app.is_main_menu = True
    translator = get_translator()
    
    # Test de traduction
    logger.info(f"Test de traduction - main_menu_title: {translator.get('main_menu_title')}")
    logger.info(f"Test de traduction - quit: {translator.get('quit')}")
    
    # Options du menu principal avec icônes modernes
    menu_options = [
        (f"{translator.get('fine_tuning_models')}", lambda: show_training_menu(app)),
        (f"{translator.get('oracle_ai_agent')}", lambda: show_oracle_menu(app)),
        (f"{translator.get('provider_config')}", lambda: show_providers_menu(app)),
        (f"{translator.get('models_management')}", lambda: show_models_menu(app)),
        (f"{translator.get('language_settings')}", lambda: show_language_menu(app)),
        (f"{translator.get('quit')}", lambda: get_app().exit())
    ]
    
    logger.info(f"Options du menu principal créées: {len(menu_options)} options")
    
    try:
        menu, kb = app.menu_manager.show_menu(f"🎻 {translator.get('main_menu_title')}", menu_options, width=50)
        logger.info("Menu principal créé avec succès")
        app.show_menu_container(menu, kb)
        logger.info("Menu principal affiché")
    except Exception as e:
        logger.error(f"Erreur lors de la création/affichage du menu principal: {e}")
        logger.exception("Détails de l'erreur:")
        raise

def show_training_menu(app):
    """Affiche le menu de formation des modèles."""
    app.is_main_menu = False
    translator = get_translator()
    
    submenu_options = [
        (f" {translator.get('llm_text')}", lambda: app.show_training_options("llm")),
        (f"{translator.get('vllm_performance')}", lambda: app.show_training_options("vllm")),
        (f"{translator.get('image_generation')}", lambda: app.show_training_options("image")),
        (f"{translator.get('voice_synthesis')}", lambda: app.show_training_options("tts")),
        (f"{translator.get('audio_generation')}", lambda: app.show_training_options("audio")),
        (f"{translator.get('return')}", lambda: show_main_menu(app))
    ]
    
    title = f"{translator.get('fine_tuning_models')}"
    menu, kb = app.menu_manager.show_menu(title, submenu_options, width=50)
    app.show_menu_container(menu, kb)

def show_oracle_menu(app):
    """Affiche le menu Oracle."""
    app.is_main_menu = False
    translator = get_translator()
    
    submenu_options = [
        (f"{translator.get('recommendation_dataset')}", lambda: show_oracle_interface(app, "recommendation")),
        (f"{translator.get('step_by_step_guide')}", lambda: show_oracle_interface(app, "guide")),
        (f"{translator.get('error_diagnostic')}", lambda: show_oracle_interface(app, "diagnostic")),
        (f"{translator.get('return')}", lambda: show_main_menu(app))
    ]
    
    title = f"{translator.get('oracle_ai_agent')}"
    menu, kb = app.menu_manager.show_menu(title, submenu_options, width=50)
    app.show_menu_container(menu, kb)

def show_models_menu(app):
    """Affiche le menu de gestion des modèles."""
    app.is_main_menu = False
    translator = get_translator()
    
    submenu_options = [
        (f"{translator.get('list_all_models')}", lambda: app.manage_model("list")),
        (f"ℹ{translator.get('model_details')}", lambda: app.manage_model("details")),
        (f"{translator.get('test_model')}", lambda: app.manage_model("test")),
        (f"{translator.get('delete_model')}", lambda: app.manage_model("delete")),
        (f"↩{translator.get('return')}", lambda: show_main_menu(app))
    ]
    
    title = f"🤖 {translator.get('models_management')}"
    menu, kb = app.menu_manager.show_menu(title, submenu_options, width=50)
    app.show_menu_container(menu, kb)

def show_language_menu(app):
    """Affiche le menu de sélection de langue."""
    app.is_main_menu = False
    translator = get_translator()
    
    language_options = [
        (f" {translator.get('english')}", lambda: (app.change_language("en"), show_main_menu(app))[1]),
        (f"{translator.get('french')}", lambda: (app.change_language("fr"), show_main_menu(app))[1]),
        (f" {translator.get('return')}", lambda: show_main_menu(app))
    ]
    
    menu, kb = app.menu_manager.show_menu(f"🌐 {translator.get('language_menu_title')}", language_options, width=40)
    app.show_menu_container(menu, kb)

def show_oracle_interface(app, oracle_mode):
    """Interface pour interagir avec Oracle."""
    app.is_main_menu = False
    translator = get_translator()
    
    options = [
        (f"{translator.get('oracle_session')} ({oracle_mode})", lambda: None),
        (translator.get("return"), lambda: show_oracle_menu(app))
    ]
    
    title = f"{translator.get('oracle_ai_agent')} - {oracle_mode}"
    menu, kb = app.menu_manager.show_menu(title, options, width=40)
    app.show_menu_container(menu, kb)
