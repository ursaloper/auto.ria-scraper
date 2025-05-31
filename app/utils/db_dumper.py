"""
Module for creating database dumps.

This module provides functions for creating backup copies (dumps)
of PostgreSQL database and managing their storage. Includes creating dumps
in SQL format and automatic cleanup of old backup copies.

Uses external pg_dump utility for creating backups,
so requires command line access and PostgreSQL client availability.

Attributes:
    logger: Logger for registering events related to dump creation.
    DUMPS_DIR: Directory for storing dumps, imported from settings.
    POSTGRES_*: Database connection parameters, imported from settings.

Functions:
    create_dump: Creates database dump with current date in filename.
    cleanup_old_dumps: Removes dumps created before specified period.
"""

import os
import subprocess
from datetime import datetime

from app.config.settings import (
    DUMPS_DIR,
    POSTGRES_DB,
    POSTGRES_HOST,
    POSTGRES_PASSWORD,
    POSTGRES_PORT,
    POSTGRES_USER,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


def create_dump() -> bool:
    """
    Creates PostgreSQL database dump.

    Forms dump filename with current date and time, then uses
    pg_dump utility to create database backup in SQL format.
    Database connection parameters are taken from application settings.

    Returns:
        bool: True if dump created successfully, False on error.

    Raises:
        Exception: Catches and logs any exceptions occurring in the process.

    Examples:
        >>> success = create_dump()
        >>> if success:
        ...     print("Dump successfully created")
        ... else:
        ...     print("Error creating dump")

    Note:
        Function requires pg_dump utility availability in the system.
        Save path for dump is created automatically based on DUMPS_DIR.
        Filename contains prefix 'autoria_dump_' and current date/time.
    """
    try:
        # Form filename with current date
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        dump_file = DUMPS_DIR / f"autoria_dump_{timestamp}.sql"

        # Form command for creating dump
        cmd = [
            "pg_dump",
            "-h",
            POSTGRES_HOST,
            "-p",
            POSTGRES_PORT,
            "-U",
            POSTGRES_USER,
            "-d",
            POSTGRES_DB,
            "-F",
            "p",  # plain text format
            "-f",
            str(dump_file),
        ]

        # Set environment variable for password
        env = os.environ.copy()
        env["PGPASSWORD"] = POSTGRES_PASSWORD

        # Execute command
        process = subprocess.run(cmd, env=env, capture_output=True, text=True)

        if process.returncode == 0:
            logger.info(f"Database dump successfully created: {dump_file}")
            return True
        else:
            logger.error(f"Error creating dump: {process.stderr}")
            return False

    except Exception as e:
        logger.error("Error creating database dump", exc_info=True)
        return False


def cleanup_old_dumps(days_to_keep: int = 30) -> None:
    """
    Removes old database dumps.

    Scans dumps directory and removes files
    that were created before specified number of days ago.
    Recognizes only files with prefix 'autoria_dump_' and extension '.sql'.

    Args:
        days_to_keep (int, optional): Number of days to keep dumps.
                                    Default is 30 days.

    Raises:
        Exception: Catches and logs any exceptions occurring in the process.

    Examples:
        >>> # Remove dumps older than 14 days
        >>> cleanup_old_dumps(14)
        >>>
        >>> # Use default value (30 days)
        >>> cleanup_old_dumps()

    Note:
        File creation date is determined by file's last modification time.
        Deletion is performed permanently, without recovery possibility.
    """
    try:
        # Get list of all files in directory
        dump_files = list(DUMPS_DIR.glob("autoria_dump_*.sql"))

        # Current date
        now = datetime.now()

        for dump_file in dump_files:
            # Get file creation date
            file_time = datetime.fromtimestamp(dump_file.stat().st_mtime)

            # If file is older than days_to_keep days, remove it
            if (now - file_time).days > days_to_keep:
                dump_file.unlink()
                logger.info(f"Removed old dump: {dump_file}")

    except Exception as e:
        logger.error("Error cleaning up old dumps", exc_info=True)
