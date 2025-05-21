"""
Корневой пакет приложения AutoRiaScraper.
"""

from app.config.celery_config import celery_app

__all__ = ['celery_app']
