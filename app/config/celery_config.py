"""
Celery settings for managing scraping tasks.

This module initializes and configures a Celery instance for scheduling
and executing scraping and backup tasks.
Settings are loaded from the settings.py module.

The module automatically creates two periodic tasks:
1. Daily data scraping from AutoRia at specified time
2. Daily database backup at specified time

Attributes:
    celery_app (Celery): Celery application instance configured
        to work with the AutoRiaScraper project.

    scraper_hour (int): Scraper start hour, extracted from SCRAPER_START_TIME.
    scraper_minute (int): Scraper start minute, extracted from SCRAPER_START_TIME.
    dump_hour (int): Backup start hour, extracted from DUMP_TIME.
    dump_minute (int): Backup start minute, extracted from DUMP_TIME.

Note:
    Celery requires a running Redis server specified in settings.
    Default timezone is set to 'Europe/Kiev'.
    Worker is configured to restart after each task to avoid memory leaks.
"""

from celery import Celery
from celery.schedules import crontab

from app.config.settings import (
    CELERY_BROKER_URL,
    CELERY_RESULT_BACKEND,
    DUMP_TIME,
    SCRAPER_START_TIME,
)

# Create Celery instance
celery_app = Celery(
    "autoria_scraper",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=["app.tasks.scraping", "app.tasks.backup"],
)

# Celery settings
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Kiev",
    enable_utc=True,
    worker_max_tasks_per_child=1,  # Restart worker after each task to avoid memory leaks
)

# Parse time from settings
scraper_hour, scraper_minute = map(int, SCRAPER_START_TIME.split(":"))
dump_hour, dump_minute = map(int, DUMP_TIME.split(":"))

# Configure periodic tasks
celery_app.conf.beat_schedule = {
    "scrape-autoria-daily": {
        "task": "app.tasks.scraping.scrape_autoria",
        "schedule": crontab(hour=scraper_hour, minute=scraper_minute),
    },
    "backup-db-daily": {
        "task": "app.tasks.backup.create_db_dump",
        "schedule": crontab(hour=dump_hour, minute=dump_minute),
    },
}

if __name__ == "__main__":
    celery_app.start()
