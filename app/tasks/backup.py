"""
Celery tasks for creating database dumps.

This module contains Celery tasks for automatic and manual creation
of backup copies (dumps) of PostgreSQL database. Tasks use functions
from utils.db_dumper module and are configured for error handling with automatic
retry attempts on failures.

Attributes:
    logger: Logger for registering backup events.
    celery_app: Celery application instance imported from configuration.

Functions:
    create_db_dump: Task for automatic DB dump creation on schedule.
    manual_backup: Task for manual DB dump creation.
"""

from app.config.celery_config import celery_app
from app.utils.db_dumper import cleanup_old_dumps, create_dump
from app.utils.logger import get_logger

logger = get_logger(__name__)


@celery_app.task(bind=True, max_retries=3, name="app.tasks.backup.create_db_dump")
def create_db_dump(self):
    """
    Task for creating database dump on schedule.

    Performs creation of PostgreSQL database backup and removes
    outdated backup copies. In case of error tries to repeat
    execution up to three times with exponential delay between attempts.

    Args:
        self: Celery task instance provided by bind=True decorator.
              Used for accessing task context and retry attempts.

    Returns:
        dict: Task execution result in dictionary format with following keys:
            - status (str): "success" or "error"
            - message (str): Operation result message
            - error (str): Error text (on failure)

    Raises:
        Exception: Any exceptions are caught and logged,
                  task is restarted using self.retry()

    Note:
        Task is configured for maximum 3 retry attempts with exponential delay.
        After successful dump creation, old dumps cleanup is automatically started.
    """
    logger.info("Starting database dump creation task")

    try:
        # Create dump
        success = create_dump()

        # Clean up old dumps (by default stored for 30 days)
        cleanup_old_dumps()

        if success:
            logger.info("Database dump successfully created")
            return {"status": "success", "message": "Database dump created successfully"}
        else:
            logger.error("Failed to create database dump")
            # Retry task on error with exponential delay
            self.retry(countdown=60 * (2**self.request.retries))
            return {"status": "error", "message": "Failed to create database dump"}

    except Exception as e:
        logger.error(f"Error creating database dump: {str(e)}", exc_info=True)
        # Retry task on error with exponential delay
        self.retry(exc=e, countdown=60 * (2**self.request.retries))

        return {"status": "error", "error": str(e)}


@celery_app.task(name="app.tasks.backup.manual_backup")
def manual_backup():
    """
    Task for manual database dump creation.

    Allows to start database backup creation process manually.
    Unlike automatic task, does not perform retry attempts on error
    and does not remove old dumps.

    Returns:
        dict: Task execution result in dictionary format with following keys:
            - status (str): "success" or "error"
            - message (str): Operation result message
            - error (str): Error text (on failure)

    Examples:
        >>> # Launch task manually
        >>> result = manual_backup.delay()
        >>>
        >>> # Check result
        >>> if result.get()["status"] == "success":
        ...     print("Backup created successfully")
    """
    logger.info("Starting manual database dump creation")

    try:
        # Create dump
        success = create_dump()

        if success:
            logger.info("Database dump successfully created")
            return {"status": "success", "message": "Database dump created successfully"}
        else:
            logger.error("Failed to create database dump")
            return {"status": "error", "message": "Failed to create database dump"}

    except Exception as e:
        logger.error(f"Error during manual dump creation: {str(e)}", exc_info=True)

        return {"status": "error", "error": str(e)}
