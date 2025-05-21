"""
Модуль настройки логирования.
Использовать ТОЛЬКО через get_logger(__name__) в каждом модуле.
"""

import logging
import logging.handlers

from app.config.settings import LOGS_DIR, LOG_LEVEL, LOG_FORMAT, LOG_DATE_FORMAT


def get_logger(name: str) -> logging.Logger:
    """
    Создает и возвращает настроенный логгер для модуля.

    Использование:
        from app.utils.logger import get_logger
        logger = get_logger(__name__)

        logger.debug("Детальная информация для отладки")
        logger.info("Информационное сообщение")
        logger.warning("Предупреждение")
        logger.error("Ошибка")
        logger.critical("Критическая ошибка")

    Args:
        name: Имя модуля (__name__)

    Returns:
        logging.Logger: Настроенный логгер
    """
    logger = logging.getLogger(name)

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
