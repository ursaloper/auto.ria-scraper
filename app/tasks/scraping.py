"""
Celery-задачи для скрапинга AutoRia (асинхронный запуск).

Этот модуль содержит задачи Celery для автоматического и ручного запуска
процесса скрапинга данных с сайта AutoRia. Задачи используют асинхронный
скрапер AutoRiaScraper и настроены на обработку ошибок с автоматическими
повторными попытками при сбоях.

Attributes:
    logger: Логгер для регистрации событий скрапинга.
    celery_app: Экземпляр приложения Celery, импортируемый из конфигурации.
    SCRAPER_START_URL: URL-адрес начальной страницы для скрапинга, импортируемый из настроек.

Functions:
    scrape_autoria: Задача для автоматического запуска скрапинга по расписанию.
    manual_scrape: Задача для ручного запуска скрапинга с указанным URL.
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
    Задача для запуска скрапинга AutoRia по расписанию.

    Выполняет полный процесс скрапинга данных с сайта AutoRia, начиная с
    указанного в настройках URL-адреса. В случае ошибки пытается повторить
    выполнение до трех раз с экспоненциальной задержкой между попытками.

    Args:
        self: Экземпляр задачи Celery, предоставляемый декоратором bind=True.
              Используется для доступа к контексту задачи и повторных попыток.

    Returns:
        dict: Результат выполнения задачи в формате словаря со следующими ключами:
            - status (str): "success" или "error"
            - processed (int): Количество обработанных автомобилей (при успехе)
            - saved (int): Количество сохраненных новых записей (при успехе)
            - error (str): Текст ошибки (при неудаче)

    Raises:
        Exception: Любые исключения перехватываются и логируются,
                  задача перезапускается с помощью self.retry()

    Note:
        Задача настроена на максимум 3 повторные попытки с экспоненциальной задержкой.
        Каждая попытка увеличивает время ожидания: 60с, 120с, 240с.
    """
    logger.info("Запуск задачи скрапинга AutoRia")

    try:
        # Создаем и запускаем скрапер
        scraper = AutoRiaScraper(
            start_url=SCRAPER_START_URL,
        )

        # Запускаем скрапинг
        stats = asyncio.run(scraper.run())

        logger.info(
            f"Скрапинг AutoRia завершен. Обработано {stats.get('processed', 0)} автомобилей, "
            f"добавлено {stats.get('saved', 0)} новых записей"
        )

        return {
            "status": "success",
            "processed": stats.get("processed", 0),
            "saved": stats.get("saved", 0),
        }

    except Exception as e:
        logger.error(f"Ошибка при выполнении задачи скрапинга: {str(e)}", exc_info=True)
        # Повторяем задачу при ошибке с экспоненциальной задержкой
        self.retry(exc=e, countdown=60 * (2**self.request.retries))

        return {"status": "error", "error": str(e)}


@celery_app.task(name="app.tasks.scraping.manual_scrape")
def manual_scrape(url=None):
    """
    Задача для ручного запуска скрапинга с указанного URL.

    Позволяет запустить процесс скрапинга вручную, с возможностью указать
    произвольный начальный URL-адрес. В отличие от автоматической задачи,
    не выполняет повторных попыток при ошибке.

    Args:
        url (str, optional): URL-адрес для начала скрапинга.
            Если не указан, используется URL по умолчанию из настроек приложения.

    Returns:
        dict: Результат выполнения задачи в формате словаря со следующими ключами:
            - status (str): "success" или "error"
            - processed (int): Количество обработанных автомобилей (при успехе)
            - saved (int): Количество сохраненных новых записей (при успехе)
            - url (str): Использованный URL-адрес
            - error (str): Текст ошибки (при неудаче)

    Examples:
        >>> # Запуск с URL по умолчанию
        >>> result = manual_scrape.delay()
        >>>
        >>> # Запуск с конкретным URL
        >>> result = manual_scrape.delay("https://auto.ria.com/uk/car/mercedes-benz/")
    """
    start_url = url or SCRAPER_START_URL
    logger.info(f"Запуск ручного скрапинга с URL: {start_url}")

    try:
        # Создаем и запускаем скрапер
        scraper = AutoRiaScraper(
            start_url=start_url,
        )

        # Запускаем скрапинг
        stats = asyncio.run(scraper.run())

        logger.info(
            f"Ручной скрапинг завершен. Обработано {stats.get('processed', 0)} автомобилей, "
            f"добавлено {stats.get('saved', 0)} новых записей"
        )

        return {
            "status": "success",
            "processed": stats.get("processed", 0),
            "saved": stats.get("saved", 0),
            "url": start_url,
        }

    except Exception as e:
        logger.error(
            f"Ошибка при выполнении ручного скрапинга: {str(e)}", exc_info=True
        )

        return {"status": "error", "error": str(e), "url": start_url}
