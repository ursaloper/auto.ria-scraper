"""
Основной модуль для запуска скрапера AutoRia.
"""

import sys
import signal
from typing import Any, NoReturn
import time

from app.core.database import init_db
from app.scraper.autoria import AutoRiaScraper
from app.utils.logger import get_logger
from app.config.settings import SCRAPER_START_URL

logger = get_logger(__name__)


def signal_handler(signum: int, frame: Any) -> NoReturn:
    """
    Обработчик сигналов для корректного завершения работы.

    Args:
        signum: Номер сигнала
        frame: Текущий фрейм выполнения
    """
    logger.info(f"Получен сигнал {signum}. Завершаем работу...")
    sys.exit(0)


def main() -> None:
    """
    Основная функция запуска скрапера.
    """
    # Регистрируем обработчики сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Инициализация базы данных (создание таблиц)
        logger.info("Инициализация базы данных...")
        init_db()

        # Создаем и запускаем скрапер
        logger.info("Запуск скрапера...")
        scraper = AutoRiaScraper(
            start_url=SCRAPER_START_URL,
            headless=True,  # В Docker всегда используем headless режим
        )

        while True:
            try:
                scraper.run()
                logger.info(
                    "Цикл сбора данных завершен. Ожидание 1 час перед следующим запуском..."
                )
                time.sleep(3600)  # Пауза 1 час между циклами
            except Exception as e:
                logger.error(f"Ошибка в цикле сбора данных: {str(e)}", exc_info=True)
                logger.info("Ожидание 5 минут перед повторной попыткой...")
                time.sleep(300)  # Пауза 5 минут при ошибке

    except Exception as e:
        logger.critical(f"Критическая ошибка: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
