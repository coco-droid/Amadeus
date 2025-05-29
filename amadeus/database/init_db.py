#!/usr/bin/env python3
"""
Database initialization script for Amadeus.
This script initializes the database, creates tables, and handles first-time setup.
"""
import os
import sys
import logging
import argparse

# Add the parent directory to sys.path to import amadeus modules
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

# Utiliser le logger sans configuration supplémentaire
logger = logging.getLogger("db_init")

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

def init_db():
    """Initialize the database and create tables"""
    from amadeus.database.session import init_db as db_init
    try:
        logger.info("Initializing database...")
        db_init()
        logger.info("Database successfully initialized.")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return False

def migrate_config():
    """Migrate provider configurations from file-based storage to DB"""
    from amadeus.core.config_manager import check_migration_needed, run_migration
    
    try:
        if check_migration_needed():
            logger.info("Configuration migration is needed. Starting migration...")
            if run_migration():
                logger.info("Configuration migration completed successfully.")
                return True
            else:
                logger.error("Configuration migration failed.")
                return False
        else:
            logger.info("No migration needed or migration already completed.")
            return True
    except Exception as e:
        logger.error(f"Migration error: {e}")
        return False

def main():
    """Main function for database initialization"""
    # Configurer le logging seulement si on exécute le script directement
    setup_script_logging()
    
    parser = argparse.ArgumentParser(
        description="Initialize the Amadeus database and perform first-time setup."
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Force initialization even if database already exists"
    )
    parser.add_argument(
        "--skip-migration", action="store_true",
        help="Skip the migration of provider configurations"
    )
    
    args = parser.parse_args()
    
    # Initialize the database
    if not init_db():
        sys.exit(1)
    
    # Migrate configurations if needed
    if not args.skip_migration:
        if not migrate_config():
            logger.warning("Configuration migration had errors. Please check the logs.")
    
    logger.info("Database setup completed successfully.")

if __name__ == "__main__":
    main()
