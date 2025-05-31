"""
Root package of the AutoRiaScraper application.

This package contains all application components for collecting data from the auto.ria.com website,
including scraper, Celery tasks, database models and utilities.

Package structure:
    config: Configuration modules (settings, Celery configuration).
    core: Base components (data models, database connection).
    scraper: Data collection components (parsers, scraper).
    tasks: Celery tasks for automation.
    utils: Helper utilities (logging, database dumps).

Attributes:
    celery_app: Celery application instance imported from configuration.
"""

from app.config.celery_config import celery_app

__all__ = ["celery_app"]
