"""
Script pour configurer les fichiers de traduction dans la structure de dossiers appropriée.
"""

import os
import json
import shutil
from pathlib import Path

def setup_translations():
    """Configuration initiale des dossiers et fichiers de traduction."""
    i18n_dir = Path(__file__).parent.absolute()
    
    # Liste des catégories et leurs clés de traduction
    categories = {
        'menus': [
            'main_menu_title', 'fine_tuning_models', 'oracle_ai_agent', 'provider_config',
            'models_management', 'language_settings', 'quit', 'add_update_provider',
            'list_configured_providers', 'delete_provider', 'return', 'back',
            'llm_text', 'vllm_performance', 'image_generation', 'voice_synthesis',
            'audio_generation', 'recommendation_dataset', 'step_by_step_guide',
            'error_diagnostic', 'list_all_models', 'model_details', 'test_model',
            'delete_model', 'language_menu_title', 'english', 'french'
        ],
        'providers': [
            'provider_type', 'cloud_providers', 'local_providers', 'available_cloud_providers',
            'available_local_providers', 'no_cloud_provider_found', 'no_local_provider_found',
            'configured_providers', 'no_configured_providers', 'provider_unavailable',
            'configuration_successful', 'configuration_saved', 'error', 'configuration_error',
            'try_again', 'delete_confirmation', 'delete_provider_confirm', 'yes', 'no',
            'deletion_successful', 'provider_deleted', 'deletion_failed', 'ok', 'type',
            'description', 'features', 'default_models', 'reconfigure', 'details',
            'unavailable'
        ],
        'ui': [
            'app_title', 'welcome_message', 'goodbye_message', 'not_implemented',
            'oracle_session', 'model_configuration', 'interactive_mode'
        ]
    }
    
    # Créer les répertoires pour chaque catégorie
    for category in categories:
        category_dir = i18n_dir / category
        category_dir.mkdir(exist_ok=True)
    
    # Ajouter aussi un répertoire 'common' pour les traductions partagées
    common_dir = i18n_dir / 'common'
    common_dir.mkdir(exist_ok=True)
    
    # Langues à traiter
    languages = ['en', 'fr']
    
    # Charger les traductions existantes
    translations = {}
    for lang in languages:
        lang_file = i18n_dir / f"{lang}.json"
        if lang_file.exists():
            with open(lang_file, 'r', encoding='utf-8') as f:
                translations[lang] = json.load(f)
    
    # Si aucune traduction existante, initialiser à partir des classes
    if not translations:
        print("Aucun fichier de traduction existant trouvé. Création des fichiers par défaut...")
        from amadeus.i18n.translator import Translator
        
        translator = Translator()
        translations = {
            'en': translator.get_default_english(),
            'fr': translator.get_default_french()
        }
    
    # Répartir les traductions par catégorie
    for lang in languages:
        if lang not in translations:
            continue
            
        # Créer un dictionnaire pour les traductions non catégorisées
        uncategorized = dict(translations[lang])
        
        # Pour chaque catégorie, créer un fichier JSON correspondant
        for category, keys in categories.items():
            category_translations = {}
            
            # Extraire les traductions pour cette catégorie
            for key in keys:
                if key in translations[lang]:
                    category_translations[key] = translations[lang][key]
                    # Supprimer du dictionnaire non catégorisé
                    if key in uncategorized:
                        del uncategorized[key]
            
            # Sauvegarder dans le fichier de catégorie
            category_file = i18n_dir / category / f"{lang}.json"
            with open(category_file, 'w', encoding='utf-8') as f:
                json.dump(category_translations, f, ensure_ascii=False, indent=2)
            
            print(f"Créé {category_file} avec {len(category_translations)} entrées.")
        
        # Sauvegarder les traductions non catégorisées dans 'common'
        if uncategorized:
            common_file = i18n_dir / 'common' / f"{lang}.json"
            with open(common_file, 'w', encoding='utf-8') as f:
                json.dump(uncategorized, f, ensure_ascii=False, indent=2)
            
            print(f"Créé {common_file} avec {len(uncategorized)} entrées non catégorisées.")
    
    print("\nMigration des traductions terminée. La nouvelle structure est prête.")
    
    # Créer des copies de sauvegarde des anciens fichiers
    for lang in languages:
        old_file = i18n_dir / f"{lang}.json"
        if old_file.exists():
            backup_file = i18n_dir / f"{lang}.json.bak"
            shutil.copy2(old_file, backup_file)
            print(f"Sauvegarde de l'ancien fichier créée: {backup_file}")

if __name__ == "__main__":
    setup_translations()
    print("\nVous pouvez maintenant supprimer les anciens fichiers JSON à la racine du dossier i18n/")
