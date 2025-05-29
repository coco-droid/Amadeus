#!/usr/bin/env python3
"""
Migration script to transfer provider configurations from file-based storage to the database.
Run this script after upgrading the Amadeus codebase to the new database-backed configuration system.
"""
import os
import sys
import logging
import argparse
from typing import Dict, Any

# Add the parent directory to sys.path to import amadeus modules
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

from amadeus.providers.config import ProviderConfigManager
from amadeus.providers.db_config import DBProviderConfigManager
from amadeus.database.session import init_db

# Utiliser le logger sans configuration supplémentaire pour éviter l'interférence
logger = logging.getLogger("config_migration")

# Configuration de logging seulement pour ce script quand exécuté directement
def setup_script_logging():
    """Configure le logging pour ce script quand il est exécuté directement."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )

def migrate_configurations():
    """
    Migrate provider configurations from file-based storage to the database.
    """
    logger.info("Initializing database...")
    init_db()
    
    # Initialize old and new config managers
    old_config = ProviderConfigManager()
    new_config = DBProviderConfigManager()
    
    logger.info("Loading existing provider configurations...")
    provider_ids = old_config.get_all_providers()
    logger.info(f"Found {len(provider_ids)} provider configurations to migrate.")
    
    success_count = 0
    for provider_id in provider_ids:
        try:
            logger.info(f"Migrating configuration for provider: {provider_id}")
            config = old_config.get_provider_config(provider_id)
            
            if not config:
                logger.warning(f"Empty configuration for provider {provider_id}, skipping.")
                continue
                
            # Save to new database-backed store
            new_config.save_provider_config(provider_id, config)
            logger.info(f"Successfully migrated configuration for provider: {provider_id}")
            success_count += 1
            
        except Exception as e:
            logger.error(f"Error migrating configuration for provider {provider_id}: {e}")
    
    logger.info(f"Migration completed. Migrated {success_count} out of {len(provider_ids)} configurations.")
    
    if success_count > 0:
        logger.info("Verifying migrations...")
        for provider_id in provider_ids:
            old_config_data = old_config.get_provider_config(provider_id)
            new_config_data = new_config.get_provider_config(provider_id)
            
            if old_config_data and new_config_data and len(old_config_data) == len(new_config_data):
                all_keys_match = all(
                    key in new_config_data and old_config_data[key] == new_config_data[key] 
                    for key in old_config_data
                )
                if all_keys_match:
                    logger.info(f"Verified configuration for provider: {provider_id}")
                else:
                    logger.warning(f"Mismatch in configuration data for provider: {provider_id}")
            elif old_config_data and not new_config_data:
                logger.warning(f"Failed to migrate configuration for provider: {provider_id}")
                
    if success_count == len(provider_ids) and len(provider_ids) > 0:
        logger.info("All configurations were successfully migrated.")
        backup_old_config()
    else:
        logger.warning(
            "Some configurations could not be migrated. "
            "The old configuration file has been preserved."
        )

def backup_old_config():
    """
    Create a backup of the old configuration file.
    """
    old_config = ProviderConfigManager()
    old_config_file = old_config.config_file
    
    if os.path.exists(old_config_file):
        backup_file = f"{old_config_file}.bak"
        try:
            logger.info(f"Creating backup of old configuration file at: {backup_file}")
            os.rename(old_config_file, backup_file)
            logger.info(f"Backup created successfully.")
            
            # Create an empty file to prevent errors in old code
            with open(old_config_file, 'wb') as f:
                f.write(b'')
                
            logger.info(
                "Old configuration file replaced with an empty file. "
                "This helps ensure compatibility with older code."
            )
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")

def main():
    """Main function to run the migration."""
    # Configurer le logging seulement si on exécute le script directement
    setup_script_logging()
    
    parser = argparse.ArgumentParser(
        description="Migrate Amadeus provider configurations from file-based storage to database."
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Force migration even if database already contains configurations"
    )
    
    args = parser.parse_args()
    
    try:
        migrate_configurations()
        logger.info("Migration completed successfully.")
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
