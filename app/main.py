"""
Основной модуль для запуска скрапера AutoRia.
"""

import sys
import signal
from typing import Any, NoReturn

from app.core.database import init_db
from app.utils.logger import get_logger

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

        # В режиме Docker-контейнера скрапер запускается через Celery
        # Эта функция используется в основном для тестирования или ручного запуска
        logger.info("Приложение готово к работе. Для запуска скрапинга используйте Celery-задачи")
        logger.info("Для ручного запуска скрапинга используйте: celery -A app call app.tasks.scraping.manual_scrape")
        logger.info("Для ручного создания дампа используйте: celery -A app call app.tasks.backup.manual_backup")

    except Exception as e:
        logger.critical(f"Критическая ошибка: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
