"""
Модуль для работы с базой данных.
"""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

from app.config.settings import DATABASE_URL
from app.core.models import Base
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Создаем движок базы данных
engine = create_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,  # Переподключение через 30 минут
)

# Создаем фабрику сессий
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """
    Инициализация базы данных.
    Создает все таблицы, если они не существуют.
    """
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("База данных успешно инициализирована")
    except SQLAlchemyError as e:
        logger.error("Ошибка при инициализации базы данных", exc_info=True)
        raise


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """
    Контекстный менеджер для работы с сессией базы данных.

    Yields:
        Session: Сессия базы данных

    Example:
        with get_db() as db:
            car = Car(...)
            db.add(car)
            db.commit()
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        logger.error("Ошибка при работе с базой данных", exc_info=True)
        raise
    finally:
        db.close()


def check_connection() -> bool:
    """
    Проверка подключения к базе данных.

    Returns:
        bool: True если подключение успешно, False в противном случае
    """
    try:
        with get_db() as db:
            db.execute("SELECT 1")
            logger.info("Подключение к базе данных успешно")
            return True
    except SQLAlchemyError as e:
        logger.error("Ошибка подключения к базе данных", exc_info=True)
        return False
