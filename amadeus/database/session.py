"""
Database session management for Amadeus.
Uses SQLite for cross-platform compatibility without external dependencies.
"""
import os
import logging
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from .models import Base

logger = logging.getLogger(__name__)

# Global session factory
SessionLocal = None
engine = None

def get_database_path() -> str:
    """
    Get the path to the SQLite database file.
    CROSS-PLATFORM: Works on Windows, macOS, and Linux.
    
    Returns:
        Path to the database file
    """
    # Use user's home directory for database storage
    home_dir = Path.home()
    amadeus_dir = home_dir / ".amadeus"
    
    # Create directory if it doesn't exist
    amadeus_dir.mkdir(exist_ok=True)
    
    # Database file path
    db_path = amadeus_dir / "amadeus.db"
    
    logger.debug(f"Database path: {db_path}")
    return str(db_path)

def init_database():
    """
    Initialize the database connection and create tables.
    CROSS-PLATFORM: Uses SQLite which is included with Python.
    """
    global SessionLocal, engine
    
    try:
        # Get database path
        db_path = get_database_path()
        
        # Create SQLite engine with connection pooling
        # Use absolute path with file:// scheme for compatibility
        db_url = f"sqlite:///{db_path}"
        
        engine = create_engine(
            db_url,
            poolclass=StaticPool,
            connect_args={
                "check_same_thread": False,  # Allow multiple threads
                "timeout": 30  # 30 second timeout
            },
            echo=False  # Set to True for SQL debugging
        )
        
        # Create session factory
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        logger.info(f"Database initialized successfully at: {db_path}")
        
        # Test the connection
        with get_session() as session:
            session.execute(text("SELECT 1"))
            logger.debug("Database connection test successful")
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

def get_session() -> Session:
    """
    Get a database session.
    
    Returns:
        SQLAlchemy session instance
        
    Raises:
        RuntimeError: If database is not initialized
    """
    global SessionLocal
    
    if SessionLocal is None:
        logger.warning("Database not initialized, attempting to initialize...")
        init_database()
    
    if SessionLocal is None:
        raise RuntimeError("Database could not be initialized")
    
    return SessionLocal()

def close_database():
    """
    Close database connections.
    """
    global SessionLocal, engine
    
    if SessionLocal:
        SessionLocal.close_all()
        SessionLocal = None
    
    if engine:
        engine.dispose()
        engine = None
    
    logger.info("Database connections closed")

# Initialize database on module import
try:
    init_database()
except Exception as e:
    logger.error(f"Failed to initialize database on import: {e}")
    # Don't raise here to avoid breaking imports
