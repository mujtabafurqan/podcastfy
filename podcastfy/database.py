"""
Database connection and session management.

This module provides database connectivity and session handling for the
Podcastfy async API, following the existing configuration patterns.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator
from dotenv import load_dotenv, find_dotenv
from .models import Base


def _load_database_config() -> str:
    """
    Load database configuration following existing config patterns.
    
    Returns:
        str: Database URL from environment variables
        
    Raises:
        ValueError: If DATABASE_URL environment variable is not found
    """
    # Try to find .env file using existing pattern from utils/config.py
    dotenv_path = find_dotenv(usecwd=True)
    if dotenv_path:
        load_dotenv(dotenv_path)
    else:
        print("Warning: .env file not found. Using environment variables if available.")
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is required")
    
    return database_url


# Initialize database connection
DATABASE_URL = _load_database_config()
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_tables():
    """Create all database tables using SQLAlchemy metadata."""
    Base.metadata.create_all(bind=engine)


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Get database session with automatic cleanup and transaction handling.
    
    Yields:
        Session: SQLAlchemy database session
        
    Usage:
        with get_db_session() as db:
            # Database operations here
            pass
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency for database sessions.
    
    Yields:
        Session: SQLAlchemy database session for FastAPI dependency injection
        
    Usage:
        @app.get("/endpoint")
        def endpoint(db: Session = Depends(get_db)):
            # Database operations here
            pass
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()