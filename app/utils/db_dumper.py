"""
Модуль для создания дампов базы данных.

Этот модуль предоставляет функции для создания резервных копий (дампов)
базы данных PostgreSQL и управления их хранением. Включает создание дампов
в формате SQL и автоматическую очистку старых резервных копий.

Использует внешнюю утилиту pg_dump для создания резервных копий,
поэтому требует доступа к командной строке и наличия PostgreSQL клиента.

Attributes:
    logger: Логгер для регистрации событий, связанных с созданием дампов.
    DUMPS_DIR: Директория для хранения дампов, импортируемая из настроек.
    POSTGRES_*: Параметры подключения к базе данных, импортируемые из настроек.

Functions:
    create_dump: Создает дамп базы данных с текущей датой в имени файла.
    cleanup_old_dumps: Удаляет дампы, созданные ранее указанного срока.
"""

import os
import subprocess
from datetime import datetime

from app.config.settings import (
    DUMPS_DIR,
    POSTGRES_DB,
    POSTGRES_HOST,
    POSTGRES_PASSWORD,
    POSTGRES_PORT,
    POSTGRES_USER,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


def create_dump() -> bool:
    """
    Создает дамп базы данных PostgreSQL.

    Формирует имя файла дампа с текущей датой и временем, затем использует
    утилиту pg_dump для создания резервной копии базы данных в формате SQL.
    Параметры подключения к базе данных берутся из настроек приложения.

    Returns:
        bool: True если дамп создан успешно, False в случае ошибки.

    Raises:
        Exception: Ловит и логирует любые исключения, возникающие в процессе.

    Examples:
        >>> success = create_dump()
        >>> if success:
        ...     print("Дамп успешно создан")
        ... else:
        ...     print("Ошибка при создании дампа")

    Note:
        Функция требует наличия утилиты pg_dump в системе.
        Путь для сохранения дампа создается автоматически на основе DUMPS_DIR.
        Имя файла содержит префикс 'autoria_dump_' и текущую дату/время.
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

    Просматривает директорию с дампами и удаляет файлы,
    которые были созданы ранее указанного количества дней назад.
    Распознает только файлы с префиксом 'autoria_dump_' и расширением '.sql'.

    Args:
        days_to_keep (int, optional): Количество дней, за которые нужно хранить дампы.
                                    По умолчанию 30 дней.

    Raises:
        Exception: Ловит и логирует любые исключения, возникающие в процессе.

    Examples:
        >>> # Удалить дампы старше 14 дней
        >>> cleanup_old_dumps(14)
        >>>
        >>> # Использовать значение по умолчанию (30 дней)
        >>> cleanup_old_dumps()

    Note:
        Дата создания файла определяется по времени последнего изменения файла.
        Удаление выполняется безвозвратно, без возможности восстановления.
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
