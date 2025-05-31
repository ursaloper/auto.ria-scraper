"""
Module for working with the database.

This module provides functions and utilities for initializing, connecting
and interacting with the PostgreSQL database. Includes functions for creating
sessions, checking connections and initializing the database schema.

Attributes:
    logger: Logger for registering database-related events.
    engine: SQLAlchemy Engine instance for database connection.
    SessionLocal: SQLAlchemy session factory for creating Session objects.

Functions:
    init_db: Initializes the database, creating all necessary tables.
    get_db: Context manager for working with database session.
    check_connection: Checks database connection.
"""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine  # type: ignore
from sqlalchemy.exc import SQLAlchemyError  # type: ignore
from sqlalchemy.orm import Session, sessionmaker  # type: ignore

from app.config.settings import DATABASE_URL
from app.core.models import Base
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Create database engine
engine = create_engine(
    DATABASE_URL,
    pool_size=5,  # Maximum number of connections in pool
    max_overflow=10,  # Maximum number of connections that can be created above pool_size
    pool_timeout=30,  # Wait time for available connection in seconds
    pool_recycle=1800,  # Reconnect after 30 minutes to prevent connection drops
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """
    Database initialization.

    Creates all tables defined in models if they don't exist.
    Uses metadata from Base to determine schema.

    Raises:
        SQLAlchemyError: If an error occurred while creating tables.

    Examples:
        >>> init_db()
        # Logs "Database successfully initialized" on successful execution
    """
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database successfully initialized")
    except SQLAlchemyError as e:
        logger.error("Error initializing database", exc_info=True)
        raise


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """
    Context manager for working with database session.

    Creates a new session and automatically manages transactions,
    performing commit on successful execution or rollback on error.
    Also ensures session closure after use.

    Yields:
        Session: SQLAlchemy database session for performing operations.

    Raises:
        SQLAlchemyError: When errors occur in database operations.

    Examples:
        >>> with get_db() as db:
        ...     car = Car(title="Toyota Camry", price_usd=15000)
        ...     db.add(car)
        # Automatically performs db.commit() when exiting the block
        # or db.rollback() when an exception occurs
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        logger.error("Error working with database", exc_info=True)
        raise
    finally:
        db.close()


def check_connection() -> bool:
    """
    Database connection check.

    Performs a simple SQL query to check database availability.
    Logs the check result.

    Returns:
        bool: True if connection is successfully established, False otherwise.

    Examples:
        >>> is_connected = check_connection()
        >>> if is_connected:
        ...     print("Database is available")
        ... else:
        ...     print("Database connection error")
    """
    try:
        with get_db() as db:
            db.execute("SELECT 1")
            logger.info("Database connection successful")
            return True
    except SQLAlchemyError as e:
        logger.error("Database connection error", exc_info=True)
        return False
