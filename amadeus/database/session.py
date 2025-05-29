"""
Database session management for Amadeus application.
Provides functions to create and manage database connections.
"""
import os
from typing import Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
import logging

from .models import Base

logger = logging.getLogger(__name__)

# Configuration
DEFAULT_DB_PATH = os.path.expanduser("~/.amadeus/amadeus.db")
DB_URL_ENV_VAR = "AMADEUS_DB_URL"

class DatabaseManager:
    """
    Database manager for Amadeus application.
    Handles database connection, session creation, and schema updates.
    """
    _instance = None
    
    def __new__(cls, db_url: Optional[str] = None):
        """Singleton pattern implementation"""
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, db_url: Optional[str] = None):
        """Initialize the database manager"""
        if self._initialized:
            return
            
        self.db_url = self._get_db_url(db_url)
        self.engine = create_engine(self.db_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self._initialized = True
        
    def _get_db_url(self, db_url: Optional[str] = None) -> str:
        """
        Determine the database URL to use.
        
        Args:
            db_url: Optional explicit database URL
            
        Returns:
            Database URL as string
        """
        if db_url:
            return db_url
            
        # Check environment variable
        env_db_url = os.environ.get(DB_URL_ENV_VAR)
        if env_db_url:
            return env_db_url
            
        # Use default SQLite database path
        os.makedirs(os.path.dirname(DEFAULT_DB_PATH), exist_ok=True)
        return f"sqlite:///{DEFAULT_DB_PATH}"
        
    def create_db_and_tables(self):
        """Create all tables defined in the models module"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info(f"Database tables created successfully at {self.db_url}")
        except SQLAlchemyError as e:
            logger.error(f"Error creating database tables: {e}")
            raise
            
    def get_session(self) -> Session:
        """
        Get a new database session.
        
        Returns:
            SQLAlchemy Session object
        """
        return self.SessionLocal()
        
    def get_db(self):
        """
        Generator for database sessions, ensures they are closed after use.
        
        Yields:
            SQLAlchemy Session object
        """
        db = self.get_session()
        try:
            yield db
        finally:
            db.close()

# Initialize the database manager with default settings
db_manager = DatabaseManager()

def init_db():
    """Initialize the database with all required tables"""
    db_manager.create_db_and_tables()
    
def get_session() -> Session:
    """
    Get a new database session.
    
    Returns:
        SQLAlchemy Session object
    """
    return db_manager.get_session()
