"""
Модуль настройки логирования.

Этот модуль предоставляет функциональность для настройки и использования
системы логирования в приложении. Реализует централизованную настройку
логирования с выводом в консоль и файл с ротацией.

Модуль следует использовать ТОЛЬКО через функцию get_logger(__name__)
в каждом модуле проекта для получения настроенного логгера.

Attributes:
    LOG_LEVEL: Уровень логирования, импортируемый из настроек.
    LOG_FORMAT: Формат записей в логе, импортируемый из настроек.
    LOG_DATE_FORMAT: Формат даты/времени в логах, импортируемый из настроек.
    LOGS_DIR: Директория для хранения файлов логов, импортируемая из настроек.

Functions:
    get_logger: Создает и возвращает настроенный логгер для модуля.
"""

import logging
import logging.handlers

from app.config.settings import (LOG_DATE_FORMAT, LOG_FORMAT, LOG_LEVEL,
                                 LOGS_DIR)


def get_logger(name: str) -> logging.Logger:
    """
    Создает и возвращает настроенный логгер для модуля.

    Настраивает логгер с выводом сообщений в консоль и в файл с ротацией.
    Файл лога ограничен размером 10 МБ с сохранением до 5 предыдущих версий.
    Если логгер для указанного имени уже был настроен, возвращает его без
    повторной настройки.

    Уровень логирования, формат сообщений и путь к файлу логов
    загружаются из настроек приложения.

    Args:
        name (str): Имя модуля, обычно передается как __name__.
                    Используется для идентификации источника сообщений в логе.

    Returns:
        logging.Logger: Настроенный логгер, готовый к использованию.

    Examples:
        >>> from app.utils.logger import get_logger
        >>> logger = get_logger(__name__)
        >>>
        >>> logger.debug("Детальная информация для отладки")
        >>> logger.info("Информационное сообщение")
        >>> logger.warning("Предупреждение")
        >>> logger.error("Ошибка")
        >>> logger.critical("Критическая ошибка")
        >>>
        >>> # Логирование с дополнительными данными
        >>> logger.info("Обработка автомобиля", extra={"car_id": 123, "url": "https://..."})
        >>>
        >>> # Логирование исключений
        >>> try:
        >>>     # какой-то код, который может вызвать исключение
        >>> except Exception as e:
        >>>     logger.error("Произошла ошибка", exc_info=True)
    """
    logger = logging.getLogger(name)
    logger.propagate = False

    # Если логгер уже настроен, возвращаем его
    if logger.handlers:
        return logger

    logger.setLevel(LOG_LEVEL)

    # Создаем форматтер
    formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

    # Хендлер для консоли
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Хендлер для файла с ротацией
    log_file = LOGS_DIR / "scraper.log"
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
