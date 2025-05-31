"""
Logging configuration module.

This module provides functionality for setting up and using
the logging system in the application. Implements centralized logging
configuration with output to console and file with rotation.

The module should ONLY be used through the get_logger(__name__)
function in each project module to get a configured logger.

Attributes:
    LOG_LEVEL: Logging level imported from settings.
    LOG_FORMAT: Log entry format imported from settings.
    LOG_DATE_FORMAT: Date/time format in logs imported from settings.
    LOGS_DIR: Directory for storing log files imported from settings.

Functions:
    get_logger: Creates and returns a configured logger for the module.
"""

import logging
import logging.handlers

from app.config.settings import LOG_DATE_FORMAT, LOG_FORMAT, LOG_LEVEL, LOGS_DIR


def get_logger(name: str) -> logging.Logger:
    """
    Creates and returns a configured logger for the module.

    Configures logger with message output to console and file with rotation.
    Log file is limited to 10 MB with up to 5 previous versions saved.
    If a logger for the specified name has already been configured, returns it without
    reconfiguration.

    Logging level, message format and log file path
    are loaded from application settings.

    Args:
        name (str): Module name, usually passed as __name__.
                    Used to identify message sources in the log.

    Returns:
        logging.Logger: Configured logger ready for use.

    Examples:
        >>> from app.utils.logger import get_logger
        >>> logger = get_logger(__name__)
        >>>
        >>> logger.debug("Detailed information for debugging")
        >>> logger.info("Informational message")
        >>> logger.warning("Warning")
        >>> logger.error("Error")
        >>> logger.critical("Critical error")
        >>>
        >>> # Logging with additional data
        >>> logger.info("Processing car", extra={"car_id": 123, "url": "https://..."})
        >>>
        >>> # Exception logging
        >>> try:
        >>>     # some code that might raise an exception
        >>> except Exception as e:
        >>>     logger.error("An error occurred", exc_info=True)
    """
    logger = logging.getLogger(name)
    logger.propagate = False

    # If logger is already configured, return it
    if logger.handlers:
        return logger

    logger.setLevel(LOG_LEVEL)

    # Create formatter
    formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler with rotation
    log_file = LOGS_DIR / "scraper.log"
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
