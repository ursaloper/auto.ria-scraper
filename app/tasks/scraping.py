"""
Celery tasks for auto.ria.com scraping (asynchronous launch).

This module contains Celery tasks for automatic and manual launch
of data scraping process from auto.ria.com website. Tasks use asynchronous
AutoRiaScraper and are configured for error handling with automatic
retry attempts on failures.

Attributes:
    logger: Logger for registering scraping events.
    celery_app: Celery application instance imported from configuration.
    SCRAPER_START_URL: Starting page URL for scraping, imported from settings.

Functions:
    scrape_autoria: Task for automatic scraping launch on schedule.
    manual_scrape: Task for manual scraping launch with specified URL.
"""

import asyncio

from app.config.celery_config import celery_app
from app.config.settings import SCRAPER_START_URL
from app.scraper.autoria import AutoRiaScraper
from app.utils.logger import get_logger

logger = get_logger(__name__)


@celery_app.task(bind=True, max_retries=3, name="app.tasks.scraping.scrape_autoria")
def scrape_autoria(self):
    """
    Task for launching auto.ria.com scraping on schedule.

    Performs full data scraping process from auto.ria.com website, starting from
    URL specified in settings. In case of error tries to repeat
    execution up to three times with exponential delay between attempts.

    Args:
        self: Celery task instance provided by bind=True decorator.
              Used for accessing task context and retry attempts.

    Returns:
        dict: Task execution result in dictionary format with following keys:
            - status (str): "success" or "error"
            - processed (int): Number of processed cars (on success)
            - saved (int): Number of saved new records (on success)
            - skipped (int): Number of skipped cars (already in DB)
            - error (str): Error text (on failure)

    Raises:
        Exception: Any exceptions are caught and logged,
                  task is restarted using self.retry()

    Note:
        Task is configured for maximum 3 retry attempts with exponential delay.
        Each attempt increases wait time: 60s, 120s, 240s.
    """
    logger.info("Starting auto.ria.com scraping task")

    try:
        # Create and run scraper
        scraper = AutoRiaScraper(
            start_url=SCRAPER_START_URL,
        )

        # Run scraping
        stats = asyncio.run(scraper.run())

        logger.info(
            f"AutoRia scraping completed. Processed {stats.get('processed', 0)} cars, "
            f"added {stats.get('saved', 0)} new records, "
            f"skipped {stats.get('skipped', 0)} (already in DB)"
        )

        return {
            "status": "success",
            "processed": stats.get("processed", 0),
            "saved": stats.get("saved", 0),
            "skipped": stats.get("skipped", 0),
        }

    except Exception as e:
        logger.error(f"Error executing scraping task: {str(e)}", exc_info=True)
        # Retry task on error with exponential delay
        self.retry(exc=e, countdown=60 * (2**self.request.retries))

        return {"status": "error", "error": str(e)}


@celery_app.task(name="app.tasks.scraping.manual_scrape")
def manual_scrape(url=None):
    """
    Task for manual scraping launch from specified URL.

    Allows to start scraping process manually, with ability to specify
    arbitrary starting URL. Unlike automatic task,
    does not perform retry attempts on error.

    Args:
        url (str, optional): URL for starting scraping.
            If not specified, uses default URL from application settings.

    Returns:
        dict: Task execution result in dictionary format with following keys:
            - status (str): "success" or "error"
            - processed (int): Number of processed cars (on success)
            - saved (int): Number of saved new records (on success)
            - skipped (int): Number of skipped cars (already in DB)
            - url (str): Used URL
            - error (str): Error text (on failure)

    Examples:
        >>> # Launch with default URL
        >>> result = manual_scrape.delay()
        >>>
        >>> # Launch with specific URL
        >>> result = manual_scrape.delay("https://auto.ria.com/uk/car/mercedes-benz/")
    """
    start_url = url or SCRAPER_START_URL
    logger.info(f"Starting manual scraping from URL: {start_url}")

    try:
        # Create and run scraper
        scraper = AutoRiaScraper(
            start_url=start_url,
        )

        # Run scraping
        stats = asyncio.run(scraper.run())

        logger.info(
            f"Manual scraping completed. Processed {stats.get('processed', 0)} cars, "
            f"added {stats.get('saved', 0)} new records, "
            f"skipped {stats.get('skipped', 0)} (already in DB)"
        )

        return {
            "status": "success",
            "processed": stats.get("processed", 0),
            "saved": stats.get("saved", 0),
            "skipped": stats.get("skipped", 0),
            "url": start_url,
        }

    except Exception as e:
        logger.error(
            f"Error executing manual scraping: {str(e)}", exc_info=True
        )

        return {"status": "error", "error": str(e), "url": start_url}
