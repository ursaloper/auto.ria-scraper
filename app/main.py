"""
Main module for launching the auto.ria.com scraper.

This module contains the application entry point function, initializes the database
and registers signal handlers for proper shutdown.
In Docker container mode, the scraper itself is launched through Celery tasks,
and this function is used for initialization and testing.

Attributes:
    logger: Logger for registering main module events.

Functions:
    signal_handler: Signal handler for proper shutdown.
    main: Main application startup function.
"""

import signal
import sys
from typing import Any, NoReturn

from app.core.database import init_db
from app.utils.logger import get_logger

logger = get_logger(__name__)


def signal_handler(signum: int, frame: Any) -> NoReturn:
    """
    Signal handler for proper shutdown.

    Intercepts termination signals (SIGINT, SIGTERM) and performs
    proper application shutdown with logging.

    Args:
        signum (int): Signal number (e.g., SIGINT = 2, SIGTERM = 15).
        frame (Any): Current execution frame (call stack information).

    Returns:
        NoReturn: Function does not return values as it terminates the process.

    Note:
        Function calls sys.exit(0), which means successful program termination.
    """
    logger.info(f"Received signal {signum}. Shutting down...")
    sys.exit(0)


def main() -> None:
    """
    Main scraper startup function.

    Performs the following operations:
    1. Registers signal handlers for proper shutdown
    2. Initializes the database (creates tables if they don't exist)
    3. Displays information about commands for manual task execution

    Returns:
        None

    Raises:
        SystemExit: In case of critical error calls sys.exit(1),
                   which means termination with error.

    Examples:
        >>> # Run application
        >>> main()

        >>> # Manual scraping launch via Celery CLI
        >>> # celery -A app call app.tasks.scraping.manual_scrape
    """
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Database initialization (table creation)
        logger.info("Initializing database...")
        init_db()

        # In Docker container mode, scraper is launched through Celery
        # This function is mainly used for testing or manual launch
        logger.info(
            "Application ready to work. Use Celery tasks to launch scraping"
        )
        logger.info(
            "For manual scraping launch use: celery -A app call app.tasks.scraping.manual_scrape"
        )
        logger.info(
            "For manual dump creation use: celery -A app call app.tasks.backup.manual_backup"
        )

    except Exception as e:
        logger.critical(f"Critical error: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
