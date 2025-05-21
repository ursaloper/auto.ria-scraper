"""
Celery-задачи для создания дампов базы данных.
"""

from app.config.celery_config import celery_app
from app.utils.db_dumper import create_dump, cleanup_old_dumps
from app.utils.logger import get_logger

logger = get_logger(__name__)


@celery_app.task(bind=True, max_retries=3, name="app.tasks.backup.create_db_dump")
def create_db_dump(self):
    """
    Задача для создания дампа базы данных.

    Args:
        self: Экземпляр задачи Celery

    Returns:
        dict: Результат выполнения задачи
    """
    logger.info("Запуск задачи создания дампа базы данных")
    
    try:
        # Создаем дамп
        success = create_dump()
        
        # Очищаем старые дампы (по умолчанию хранятся 30 дней)
        cleanup_old_dumps()
        
        if success:
            logger.info("Дамп базы данных успешно создан")
            return {
                "status": "success",
                "message": "Дамп базы данных создан успешно"
            }
        else:
            logger.error("Не удалось создать дамп базы данных")
            # Повторяем задачу при ошибке с экспоненциальной задержкой
            self.retry(countdown=60 * (2 ** self.request.retries))
            return {
                "status": "error",
                "message": "Не удалось создать дамп базы данных"
            }
        
    except Exception as e:
        logger.error(f"Ошибка при создании дампа базы данных: {str(e)}", exc_info=True)
        # Повторяем задачу при ошибке с экспоненциальной задержкой
        self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
        
        return {
            "status": "error",
            "error": str(e)
        }


@celery_app.task(name="app.tasks.backup.manual_backup")
def manual_backup():
    """
    Задача для ручного создания дампа базы данных.
    
    Returns:
        dict: Результат выполнения задачи
    """
    logger.info("Запуск ручного создания дампа базы данных")
    
    try:
        # Создаем дамп
        success = create_dump()
        
        if success:
            logger.info("Дамп базы данных успешно создан")
            return {
                "status": "success",
                "message": "Дамп базы данных создан успешно"
            }
        else:
            logger.error("Не удалось создать дамп базы данных")
            return {
                "status": "error",
                "message": "Не удалось создать дамп базы данных"
            }
        
    except Exception as e:
        logger.error(f"Ошибка при ручном создании дампа: {str(e)}", exc_info=True)
        
        return {
            "status": "error",
            "error": str(e)
        } 