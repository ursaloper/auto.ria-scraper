"""
Основной модуль для запуска скрапера AutoRia.

Этот модуль содержит функцию точки входа в приложение, инициализирует базу данных
и регистрирует обработчики сигналов для корректного завершения работы.
В режиме Docker-контейнера сам скрапер запускается через задачи Celery,
а эта функция используется для инициализации и тестирования.

Attributes:
    logger: Логгер для регистрации событий основного модуля.

Functions:
    signal_handler: Обработчик сигналов для корректного завершения работы.
    main: Основная функция запуска приложения.
"""

import signal
import sys
from typing import Any, NoReturn

from app.core.database import init_db
from app.utils.logger import get_logger

logger = get_logger(__name__)


def signal_handler(signum: int, frame: Any) -> NoReturn:
    """
    Обработчик сигналов для корректного завершения работы.

    Перехватывает сигналы завершения (SIGINT, SIGTERM) и выполняет
    корректное завершение работы приложения с логированием.

    Args:
        signum (int): Номер сигнала (например, SIGINT = 2, SIGTERM = 15).
        frame (Any): Текущий фрейм выполнения (информация стека вызовов).

    Returns:
        NoReturn: Функция не возвращает значения, так как завершает процесс.

    Note:
        Функция вызывает sys.exit(0), что означает успешное завершение программы.
    """
    logger.info(f"Получен сигнал {signum}. Завершаем работу...")
    sys.exit(0)


def main() -> None:
    """
    Основная функция запуска скрапера.

    Выполняет следующие операции:
    1. Регистрирует обработчики сигналов для корректного завершения работы
    2. Инициализирует базу данных (создает таблицы, если они не существуют)
    3. Выводит информацию о командах для ручного запуска задач

    Returns:
        None

    Raises:
        SystemExit: В случае критической ошибки вызывает sys.exit(1),
                   что означает завершение с ошибкой.

    Examples:
        >>> # Запуск приложения
        >>> main()

        >>> # Ручной запуск скрапинга через Celery CLI
        >>> # celery -A app call app.tasks.scraping.manual_scrape
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
        logger.info(
            "Приложение готово к работе. Для запуска скрапинга используйте Celery-задачи"
        )
        logger.info(
            "Для ручного запуска скрапинга используйте: celery -A app call app.tasks.scraping.manual_scrape"
        )
        logger.info(
            "Для ручного создания дампа используйте: celery -A app call app.tasks.backup.manual_backup"
        )

    except Exception as e:
        logger.critical(f"Критическая ошибка: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
