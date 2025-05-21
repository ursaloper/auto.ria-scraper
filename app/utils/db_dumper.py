"""
Модуль для создания дампов базы данных.
"""

import os
from datetime import datetime
import subprocess

from app.config.settings import (
    DUMPS_DIR,
    POSTGRES_DB,
    POSTGRES_USER,
    POSTGRES_PASSWORD,
    POSTGRES_HOST,
    POSTGRES_PORT,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


def create_dump() -> bool:
    """
    Создает дамп базы данных.

    Returns:
        bool: True если дамп создан успешно, False в противном случае
    """
    try:
        # Формируем имя файла с текущей датой
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        dump_file = DUMPS_DIR / f"autoria_dump_{timestamp}.sql"

        # Формируем команду для создания дампа
        cmd = [
            "pg_dump",
            "-h",
            POSTGRES_HOST,
            "-p",
            POSTGRES_PORT,
            "-U",
            POSTGRES_USER,
            "-d",
            POSTGRES_DB,
            "-F",
            "p",  # plain text format
            "-f",
            str(dump_file),
        ]

        # Устанавливаем переменную окружения для пароля
        env = os.environ.copy()
        env["PGPASSWORD"] = POSTGRES_PASSWORD

        # Выполняем команду
        process = subprocess.run(cmd, env=env, capture_output=True, text=True)

        if process.returncode == 0:
            logger.info(f"Дамп базы данных успешно создан: {dump_file}")
            return True
        else:
            logger.error(f"Ошибка при создании дампа: {process.stderr}")
            return False

    except Exception as e:
        logger.error("Ошибка при создании дампа базы данных", exc_info=True)
        return False


def cleanup_old_dumps(days_to_keep: int = 30) -> None:
    """
    Удаляет старые дампы базы данных.

    Args:
        days_to_keep (int): Количество дней, за которые нужно хранить дампы
    """
    try:
        # Получаем список всех файлов в директории
        dump_files = list(DUMPS_DIR.glob("autoria_dump_*.sql"))

        # Текущая дата
        now = datetime.now()

        for dump_file in dump_files:
            # Получаем дату создания файла
            file_time = datetime.fromtimestamp(dump_file.stat().st_mtime)

            # Если файл старше days_to_keep дней, удаляем его
            if (now - file_time).days > days_to_keep:
                dump_file.unlink()
                logger.info(f"Удален старый дамп: {dump_file}")

    except Exception as e:
        logger.error("Ошибка при очистке старых дампов", exc_info=True)
