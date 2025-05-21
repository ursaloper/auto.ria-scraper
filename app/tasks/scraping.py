"""
Celery-задачи для скрапинга AutoRia.
"""

from app.config.celery_config import celery_app
from app.scraper.autoria import AutoRiaScraper
from app.config.settings import SCRAPER_START_URL
from app.utils.logger import get_logger

logger = get_logger(__name__)


@celery_app.task(bind=True, max_retries=3, name="app.tasks.scraping.scrape_autoria")
def scrape_autoria(self):
    """
    Задача для запуска скрапинга AutoRia.

    Args:
        self: Экземпляр задачи Celery

    Returns:
        dict: Результат выполнения задачи
    """
    logger.info("Запуск задачи скрапинга AutoRia")
    
    try:
        # Создаем и запускаем скрапер
        scraper = AutoRiaScraper(
            start_url=SCRAPER_START_URL,
            headless=True,  # В Docker всегда используем headless режим
        )
        
        # Запускаем скрапинг
        stats = scraper.run()
        
        logger.info(f"Скрапинг AutoRia завершен. Обработано {stats.get('processed', 0)} автомобилей, "
                    f"добавлено {stats.get('saved', 0)} новых записей")
        
        return {
            "status": "success",
            "processed": stats.get("processed", 0),
            "saved": stats.get("saved", 0)
        }
        
    except Exception as e:
        logger.error(f"Ошибка при выполнении задачи скрапинга: {str(e)}", exc_info=True)
        # Повторяем задачу при ошибке с экспоненциальной задержкой
        self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
        
        return {
            "status": "error",
            "error": str(e)
        }


@celery_app.task(name="app.tasks.scraping.manual_scrape")
def manual_scrape(url=None):
    """
    Задача для ручного запуска скрапинга с указанного URL.
    
    Args:
        url (str, optional): URL для начала скрапинга.
            Если не указан, используется URL по умолчанию.
            
    Returns:
        dict: Результат выполнения задачи
    """
    start_url = url or SCRAPER_START_URL
    logger.info(f"Запуск ручного скрапинга с URL: {start_url}")
    
    try:
        # Создаем и запускаем скрапер
        scraper = AutoRiaScraper(
            start_url=start_url,
            headless=True,
        )
        
        # Запускаем скрапинг
        stats = scraper.run()
        
        logger.info(f"Ручной скрапинг завершен. Обработано {stats.get('processed', 0)} автомобилей, "
                   f"добавлено {stats.get('saved', 0)} новых записей")
        
        return {
            "status": "success",
            "processed": stats.get("processed", 0),
            "saved": stats.get("saved", 0),
            "url": start_url
        }
        
    except Exception as e:
        logger.error(f"Ошибка при выполнении ручного скрапинга: {str(e)}", exc_info=True)
        
        return {
            "status": "error",
            "error": str(e),
            "url": start_url
        } 