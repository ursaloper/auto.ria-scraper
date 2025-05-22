"""
Celery-задачи для создания дампов базы данных.

Этот модуль содержит задачи Celery для автоматического и ручного создания
резервных копий (дампов) базы данных PostgreSQL. Задачи используют функции
из модуля utils.db_dumper и настроены на обработку ошибок с автоматическими
повторными попытками при сбоях.

Attributes:
    logger: Логгер для регистрации событий резервного копирования.
    celery_app: Экземпляр приложения Celery, импортируемый из конфигурации.

Functions:
    create_db_dump: Задача для автоматического создания дампа БД по расписанию.
    manual_backup: Задача для ручного создания дампа БД.
"""

from app.config.celery_config import celery_app
from app.utils.db_dumper import cleanup_old_dumps, create_dump
from app.utils.logger import get_logger

logger = get_logger(__name__)


@celery_app.task(bind=True, max_retries=3, name="app.tasks.backup.create_db_dump")
def create_db_dump(self):
    """
    Задача для создания дампа базы данных по расписанию.

    Выполняет создание резервной копии базы данных PostgreSQL и удаляет
    устаревшие резервные копии. В случае ошибки пытается повторить
    выполнение до трех раз с экспоненциальной задержкой между попытками.

    Args:
        self: Экземпляр задачи Celery, предоставляемый декоратором bind=True.
              Используется для доступа к контексту задачи и повторных попыток.

    Returns:
        dict: Результат выполнения задачи в формате словаря со следующими ключами:
            - status (str): "success" или "error"
            - message (str): Сообщение о результате операции
            - error (str): Текст ошибки (при неудаче)

    Raises:
        Exception: Любые исключения перехватываются и логируются,
                  задача перезапускается с помощью self.retry()

    Note:
        Задача настроена на максимум 3 повторные попытки с экспоненциальной задержкой.
        После успешного создания дампа автоматически запускается очистка старых дампов.
    """
    logger.info("Запуск задачи создания дампа базы данных")

    try:
        # Создаем дамп
        success = create_dump()

        # Очищаем старые дампы (по умолчанию хранятся 30 дней)
        cleanup_old_dumps()

        if success:
            logger.info("Дамп базы данных успешно создан")
            return {"status": "success", "message": "Дамп базы данных создан успешно"}
        else:
            logger.error("Не удалось создать дамп базы данных")
            # Повторяем задачу при ошибке с экспоненциальной задержкой
            self.retry(countdown=60 * (2**self.request.retries))
            return {"status": "error", "message": "Не удалось создать дамп базы данных"}

    except Exception as e:
        logger.error(f"Ошибка при создании дампа базы данных: {str(e)}", exc_info=True)
        # Повторяем задачу при ошибке с экспоненциальной задержкой
        self.retry(exc=e, countdown=60 * (2**self.request.retries))

        return {"status": "error", "error": str(e)}


@celery_app.task(name="app.tasks.backup.manual_backup")
def manual_backup():
    """
    Задача для ручного создания дампа базы данных.

    Позволяет запустить процесс создания резервной копии базы данных вручную.
    В отличие от автоматической задачи, не выполняет повторных попыток при ошибке
    и не удаляет старые дампы.

    Returns:
        dict: Результат выполнения задачи в формате словаря со следующими ключами:
            - status (str): "success" или "error"
            - message (str): Сообщение о результате операции
            - error (str): Текст ошибки (при неудаче)

    Examples:
        >>> # Запуск задачи вручную
        >>> result = manual_backup.delay()
        >>>
        >>> # Проверка результата
        >>> if result.get()["status"] == "success":
        ...     print("Резервная копия создана успешно")
    """
    logger.info("Запуск ручного создания дампа базы данных")

    try:
        # Создаем дамп
        success = create_dump()

        if success:
            logger.info("Дамп базы данных успешно создан")
            return {"status": "success", "message": "Дамп базы данных создан успешно"}
        else:
            logger.error("Не удалось создать дамп базы данных")
            return {"status": "error", "message": "Не удалось создать дамп базы данных"}

    except Exception as e:
        logger.error(f"Ошибка при ручном создании дампа: {str(e)}", exc_info=True)

        return {"status": "error", "error": str(e)}
