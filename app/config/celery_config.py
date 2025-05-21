"""
Настройки Celery для управления задачами скрапинга.
"""

from celery import Celery
from celery.schedules import crontab

from app.config.settings import (
    CELERY_BROKER_URL, 
    CELERY_RESULT_BACKEND,
    SCRAPER_START_TIME,
    DUMP_TIME
)

# Создаем экземпляр Celery
celery_app = Celery('autoria_scraper',
                    broker=CELERY_BROKER_URL,
                    backend=CELERY_RESULT_BACKEND,
                    include=['app.tasks.scraping', 'app.tasks.backup'])

# Настройки Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Europe/Kiev',
    enable_utc=True,
    worker_max_tasks_per_child=1,  # Перезапускать worker после каждой задачи для избежания утечек памяти
)

# Парсим время из настроек
scraper_hour, scraper_minute = map(int, SCRAPER_START_TIME.split(':'))
dump_hour, dump_minute = map(int, DUMP_TIME.split(':'))

# Настройка периодических задач
celery_app.conf.beat_schedule = {
    'scrape-autoria-daily': {
        'task': 'app.tasks.scraping.scrape_autoria',
        'schedule': crontab(hour=scraper_hour, minute=scraper_minute),
    },
    'backup-db-daily': {
        'task': 'app.tasks.backup.create_db_dump',
        'schedule': crontab(hour=dump_hour, minute=dump_minute),
    },
}

if __name__ == '__main__':
    celery_app.start() 