import os
import json
import logging
from typing import Dict, Optional, List, Set

# Configuration du logging avec le nouveau système
logger = logging.getLogger("amadeus.i18n")

# Singleton pour le traducteur actif
_current_translator = None

def get_translator() -> 'Translator':
    """Retourne l'instance du traducteur actif."""
    global _current_translator
    if _current_translator is None:
        _current_translator = Translator()
    return _current_translator

def set_language(language_code: str) -> bool:
    """Change la langue active du traducteur.
    
    Args:
        language_code: Code de la langue à utiliser (ex: 'fr', 'en')
        
    Returns:
        bool: True si la langue a été changée avec succès, False sinon
    """
    translator = get_translator()
    return translator.set_language(language_code)

def get_available_languages() -> List[str]:
    """Retourne la liste des langues disponibles."""
    translator = get_translator()
    return translator.get_available_languages()

def translate(key: str, default: Optional[str] = None) -> str:
    """Fonction raccourcie pour traduire une clé.
    
    Args:
        key: Clé de traduction à utiliser (format: 'dir.access_key' ou 'access_key')
        default: Valeur par défaut si la clé n'est pas trouvée
        
    Returns:
        str: La traduction ou la valeur par défaut
    """
    translator = get_translator()
    return translator.get(key, default)

class Translator:
    """Gère les traductions pour l'application Amadeus."""
    
    def __init__(self, language: str = "en"):
        """Initialise le traducteur.
        
        Args:
            language: Langue par défaut à utiliser
        """
        self.translations: Dict[str, Dict[str, str]] = {}
        self.current_language = language
        self.directories: Set[str] = set()
        self.available_languages: Set[str] = set()
        self.missing_keys: Dict[str, Set[str]] = {}  # Track missing keys per language
        self.load_translations()
    
    def load_translations(self) -> None:
        """Charge les fichiers de traduction depuis tous les sous-dossiers."""
        # Chemin du dossier des traductions - Corriger pour utiliser le répertoire source
        i18n_dir = os.path.dirname(os.path.abspath(__file__))
        
        logger.info(f"Répertoire initial détecté: {i18n_dir}")
        
        # Si on est dans venv, chercher dans le répertoire source
        if 'venv' in i18n_dir or 'site-packages' in i18n_dir:
            logger.info("Détection d'exécution depuis venv, recherche du répertoire source...")
            # Remonter jusqu'au répertoire racine du projet
            current_dir = os.getcwd()
            logger.info(f"Répertoire de travail actuel: {current_dir}")
            
            possible_paths = [
                os.path.join(current_dir, 'amadeus', 'i18n'),
                os.path.join(os.path.dirname(current_dir), 'amadeus', 'i18n'),
                '/home/t4x/Desktop/Amadeus/amadeus/i18n',
                # Essayer de remonter plus haut
                os.path.join(current_dir, '..', 'amadeus', 'i18n'),
                os.path.join(current_dir, '..', '..', 'amadeus', 'i18n')
            ]
            
            logger.debug(f"Chemins testés: {possible_paths}")
            
            for path in possible_paths:
                abs_path = os.path.abspath(path)
                logger.debug(f"Test du chemin: {abs_path} - Existe: {os.path.exists(abs_path)}")
                if os.path.exists(abs_path):
                    i18n_dir = abs_path
                    logger.info(f"Répertoire source trouvé: {i18n_dir}")
                    break
            else:
                # Fallback : utiliser le répertoire original même s'il est dans venv
                logger.warning(f"Impossible de trouver le répertoire source, utilisation de {i18n_dir}")
        
        logger.info(f"Recherche des traductions dans: {i18n_dir}")
        
        # Vérifier que le répertoire existe et est lisible
        if not os.path.exists(i18n_dir):
            logger.error(f"Le répertoire {i18n_dir} n'existe pas!")
            self._initialize_default_translations()
            return
            
        if not os.access(i18n_dir, os.R_OK):
            logger.error(f"Le répertoire {i18n_dir} n'est pas lisible!")
            self._initialize_default_translations()
            return
        
        files_found = []
        directories_scanned = []
        
        try:
            # Parcourir tous les sous-dossiers dans i18n
            for root, dirs, files in os.walk(i18n_dir):
                directories_scanned.append(root)
                logger.debug(f"Scan du répertoire: {root}")
                logger.debug(f"Fichiers trouvés: {files}")
                
                for file in files:
                    if file.endswith('.json') and not file.startswith('.'):
                        # Extraire le code de langue du nom du fichier (ex: 'en.json' -> 'en')
                        language_code = os.path.splitext(file)[0]
                        
                        # Ignorer les fichiers qui ne sont pas des codes de langue valides
                        if language_code not in ['en', 'fr', 'es', 'de', 'it', 'pt', 'ru', 'zh', 'ja', 'ko']:
                            logger.debug(f"Fichier ignoré (pas un code de langue valide): {file}")
                            continue
                        
                        self.available_languages.add(language_code)
                        
                        # Déterminer le répertoire/catégorie en fonction du chemin relatif
                        rel_path = os.path.relpath(root, i18n_dir)
                        if rel_path == '.':
                            # Fichier à la racine - catégorie 'common'
                            directory = 'common'
                        else:
                            # Fichier dans un sous-dossier
                            directory = rel_path.replace(os.sep, '_')  # Gérer les sous-dossiers imbriqués
                        
                        self.directories.add(directory)
                        
                        # Charger les traductions
                        file_path = os.path.join(root, file)
                        files_found.append(file_path)
                        logger.info(f"Fichier de traduction trouvé: {file_path}")
                        self._load_translation_file(file_path, language_code, directory)
        
        except Exception as e:
            logger.error(f"Erreur lors du parcours du répertoire {i18n_dir}: {e}")
            logger.exception("Détails de l'erreur:")
        
        # Logging détaillé de la recherche
        logger.info(f"Répertoires scannés: {directories_scanned}")
        logger.info(f"Fichiers de traduction trouvés: {files_found}")
        
        # Si aucune traduction n'est trouvée, initialiser avec des valeurs par défaut
        if not files_found or not self.translations:
            logger.warning(f"Aucun fichier de traduction trouvé dans {i18n_dir} et ses sous-répertoires")
            logger.warning(f"Répertoires scannés sans succès: {directories_scanned}")
            self._initialize_default_translations()
        else:
            logger.info(f"Langues disponibles: {', '.join(sorted(self.available_languages))}")
            logger.info(f"Répertoires chargés: {', '.join(sorted(self.directories))}")
            
            # Log du nombre de traductions par langue et répertoire
            for lang in self.available_languages:
                total_keys = len(self.translations.get(lang, {}))
                logger.info(f"Langue '{lang}': {total_keys} traductions chargées")
                
                # Afficher quelques clés pour vérification
                sample_keys = list(self.translations.get(lang, {}).keys())[:5]
                logger.debug(f"  Exemples de clés: {sample_keys}")
    
    def _load_translation_file(self, file_path: str, language_code: str, directory: str) -> None:
        """Charge un fichier de traduction spécifique.
        
        Args:
            file_path: Chemin vers le fichier de traduction
            language_code: Code de la langue du fichier
            directory: Répertoire/catégorie des traductions (ex: 'menus', 'providers', 'common')
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                translations = json.load(f)
                
                # Initialiser le dictionnaire de langue s'il n'existe pas encore
                if language_code not in self.translations:
                    self.translations[language_code] = {}
                
                # Ajouter les traductions avec le format 'directory.key'
                loaded_keys = []
                for key, value in translations.items():
                    if directory == 'common':
                        # Pour les fichiers communs, stocker directement la clé
                        self.translations[language_code][key] = value
                        loaded_keys.append(key)
                    else:
                        # Pour les répertoires spécifiques, utiliser le format 'directory.key'
                        full_key = f"{directory}.{key}"
                        self.translations[language_code][full_key] = value
                        loaded_keys.append(full_key)
                    
                logger.info(f"Chargé {len(translations)} traductions depuis {file_path} (répertoire: {directory})")
                logger.debug(f"Clés chargées: {', '.join(loaded_keys[:10])}{'...' if len(loaded_keys) > 10 else ''}")
        except Exception as e:
            logger.error(f"Erreur lors du chargement du fichier {file_path}: {e}")
    
    def _initialize_default_translations(self) -> None:
        """Initialise les traductions par défaut si aucun fichier n'est trouvé."""
        # Créer des traductions minimales pour éviter les erreurs
        self.translations['en'] = self.get_default_english()
        self.translations['fr'] = self.get_default_french()
        self.available_languages.update(['en', 'fr'])
        self.directories.add('common')
        self.directories.add('menus')
        self.directories.add('providers')
        
        logger.info("Traductions par défaut initialisées")
        logger.info(f"Langues par défaut: {list(self.available_languages)}")
        logger.info(f"Répertoires par défaut: {list(self.directories)}")
    
    def get_default_english(self) -> Dict[str, str]:
        """Fournit les traductions anglaises par défaut."""
        return {
            # Common/UI translations
            "app_title": "Amadeus - Fine-Tuning Assistant for Generative AI Models",
            "welcome_message": "Welcome to Amadeus!",
            "goodbye_message": "Thank you for using Amadeus!",
            "not_implemented": "This feature is not yet implemented",
            "oracle_session": "🔮 Start Oracle session",
            "model_configuration": "📝 Configuration of",
            "interactive_mode": "🔨 Interactive mode for",
            
            # Menu translations with directory prefix
            "menus.main_menu_title": "Main Menu",
            "menus.fine_tuning_models": "➤ Fine-tuning Models",
            "menus.oracle_ai_agent": "🔍 Oracle (AI Agent)",
            "menus.provider_config": "⚙️ Provider Configuration",
            "menus.models_management": "📂 Models Management",
            "menus.language_settings": "🌐 Language Settings",
            "menus.quit": "🚪 Quit",
            "menus.return": "↩️ Return",
            "menus.back": "⬅️ Back",
            "menus.language_menu_title": "Language Selection",
            "menus.english": "🇬🇧 English",
            "menus.french": "🇫🇷 Français",
            
            # Provider translations with directory prefix
            "providers.cloud_providers": "☁️ Cloud Providers",
            "providers.local_providers": "💻 Local Providers",
            "providers.provider_type": "Provider Type",
            "providers.add_update_provider": "➕ Add or Update a provider",
            "providers.list_configured_providers": "🔄 List configured providers",
            "providers.delete_provider": "🗑️ Delete a provider",
            "providers.configured_providers": "Configured providers",
            "providers.no_configured_providers": "No provider is currently configured.",
            "providers.configuration_successful": "Configuration successful",
            "providers.error": "Error",
            "providers.ok": "OK",
            "providers.yes": "Yes",
            "providers.no": "No"
        }
    
    def get_default_french(self) -> Dict[str, str]:
        """Fournit les traductions françaises par défaut."""
        return {
            # Common/UI translations
            "app_title": "Amadeus - Assistant de Fine-Tuning pour Modèles d'IA Générative",
            "welcome_message": "Bienvenue sur Amadeus !",
            "goodbye_message": "Merci d'avoir utilisé Amadeus !",
            "not_implemented": "Cette fonctionnalité n'est pas encore implémentée",
            "oracle_session": "🔮 Démarrer session Oracle",
            "model_configuration": "📝 Configuration de",
            "interactive_mode": "🔨 Mode interactif pour",
            
            # Menu translations with directory prefix
            "menus.main_menu_title": "Menu Principal",
            "menus.fine_tuning_models": "➤ Fine-tuning de modèles",
            "menus.oracle_ai_agent": "🔍 Oracle (Agent IA)",
            "menus.provider_config": "⚙️ Configuration des fournisseurs",
            "menus.models_management": "📂 Gestion des Modèles",
            "menus.language_settings": "🌐 Paramètres de langue",
            "menus.quit": "🚪 Quitter",
            "menus.return": "↩️ Retour",
            "menus.back": "⬅️ Retour",
            "menus.language_menu_title": "Sélection de la langue",
            "menus.english": "🇬🇧 Anglais",
            "menus.french": "🇫🇷 Français",
            
            # Provider translations with directory prefix
            "providers.cloud_providers": "☁️ Cloud Providers",
            "providers.local_providers": "💻 Local Providers",
            "providers.provider_type": "Type de Provider",
            "providers.add_update_provider": "➕ Ajouter ou Mettre à jour un provider",
            "providers.list_configured_providers": "🔄 Lister providers configurés",
            "providers.delete_provider": "🗑️ Supprimer un provider",
            "providers.configured_providers": "Providers configurés",
            "providers.no_configured_providers": "Aucun provider n'est configuré actuellement.",
            "providers.configuration_successful": "Configuration réussie",
            "providers.error": "Erreur",
            "providers.ok": "OK",
            "providers.yes": "Oui",
            "providers.no": "Non"
        }
    
    def get_available_languages(self) -> List[str]:
        """Retourne la liste des langues disponibles."""
        return list(self.available_languages)
    
    def set_language(self, language_code: str) -> bool:
        """Change la langue active."""
        if language_code in self.available_languages:
            old_language = self.current_language
            self.current_language = language_code
            logger.debug(f"Langue changée de '{old_language}' vers '{language_code}'")
            return True
        else:
            logger.warning(f"Langue non disponible: {language_code}. Langues disponibles: {list(self.available_languages)}")
            return False
    
    def get(self, key: str, default: Optional[str] = None) -> str:
        """Récupère une traduction par sa clé.
        
        Support des formats:
        - 'directory.access_key' (ex: 'menus.main_menu_title')
        - 'access_key' (recherche dans common d'abord, puis dans tous les répertoires)
        
        Args:
            key: Clé de traduction à utiliser
            default: Valeur par défaut si la clé n'est pas trouvée
            
        Returns:
            str: La traduction ou la valeur par défaut
        """
        searched_locations = []
        current_lang = self.current_language
        
        # Essayer d'obtenir la traduction dans la langue actuelle
        translations = self.translations.get(current_lang, {})
        
        # Si la clé contient un point, c'est le format 'directory.access_key'
        if '.' in key:
            searched_locations.append(f"'{key}' dans langue '{current_lang}'")
            if key in translations:
                logger.debug(f"Traduction trouvée pour '{key}' en '{current_lang}': '{translations[key]}'")
                return translations[key]
        else:
            # Pour les clés sans préfixe, chercher d'abord dans common
            searched_locations.append(f"'{key}' dans common (langue '{current_lang}')")
            if key in translations:
                logger.debug(f"Traduction trouvée pour '{key}' en '{current_lang}' (common): '{translations[key]}'")
                return translations[key]
            
            # Puis chercher dans tous les répertoires
            for directory in sorted(self.directories):
                if directory != 'common':
                    full_key = f"{directory}.{key}"
                    searched_locations.append(f"'{full_key}' dans répertoire '{directory}' (langue '{current_lang}')")
                    if full_key in translations:
                        logger.debug(f"Traduction trouvée pour '{key}' en '{current_lang}' (répertoire '{directory}'): '{translations[full_key]}'")
                        return translations[full_key]
        
        # Fallback sur l'anglais si la langue courante n'est pas l'anglais
        if current_lang != 'en':
            en_translations = self.translations.get('en', {})
            if '.' in key:
                searched_locations.append(f"'{key}' dans langue 'en' (fallback)")
                if key in en_translations:
                    logger.debug(f"Traduction fallback trouvée pour '{key}' en anglais: '{en_translations[key]}'")
                    return en_translations[key]
            else:
                # Chercher d'abord dans common en anglais
                searched_locations.append(f"'{key}' dans common (langue 'en' - fallback)")
                if key in en_translations:
                    logger.debug(f"Traduction fallback trouvée pour '{key}' en anglais (common): '{en_translations[key]}'")
                    return en_translations[key]
                
                # Puis chercher dans tous les répertoires en anglais
                for directory in sorted(self.directories):
                    if directory != 'common':
                        full_key = f"{directory}.{key}"
                        searched_locations.append(f"'{full_key}' dans répertoire '{directory}' (langue 'en' - fallback)")
                        if full_key in en_translations:
                            logger.debug(f"Traduction fallback trouvée pour '{key}' en anglais (répertoire '{directory}'): '{en_translations[full_key]}'")
                            return en_translations[full_key]
        
        # Retourner la clé elle-même ou la valeur par défaut
        result = default if default is not None else key
        
        # Log détaillé des échecs de traduction
        logger.warning(f"Traduction non trouvée pour la clé '{key}'")
        logger.warning(f"Emplacements recherchés: {searched_locations}")
        logger.warning(f"Langues disponibles: {list(self.available_languages)}")
        logger.warning(f"Répertoires disponibles: {list(self.directories)}")
        logger.warning(f"Langue actuelle: '{current_lang}'")
        logger.warning(f"Retour de la valeur: '{result}'")
        
        # Tracking des clés manquantes pour statistiques
        if current_lang not in self.missing_keys:
            self.missing_keys[current_lang] = set()
        self.missing_keys[current_lang].add(key)
        
        return result
    
    def get_missing_keys_report(self) -> str:
        """Génère un rapport des clés de traduction manquantes."""
        if not self.missing_keys:
            return "Aucune clé de traduction manquante détectée."
        
        report = ["Rapport des clés de traduction manquantes:"]
        for lang, keys in self.missing_keys.items():
            report.append(f"\nLangue '{lang}': {len(keys)} clés manquantes")
            for key in sorted(keys):
                report.append(f"  - {key}")
        
        return "\n".join(report)
    
    def __call__(self, key: str, default: Optional[str] = None) -> str:
        """Permet d'utiliser l'instance du traducteur directement comme fonction."""
        return self.get(key, default)
