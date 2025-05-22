"""
Модуль для работы с базой данных.

Этот модуль предоставляет функции и утилиты для инициализации, подключения
и взаимодействия с базой данных PostgreSQL. Включает в себя функции для создания
сессий, проверки соединения и инициализации схемы базы данных.

Attributes:
    logger: Логгер для регистрации событий, связанных с базой данных.
    engine: Экземпляр SQLAlchemy Engine для подключения к базе данных.
    SessionLocal: Фабрика сессий SQLAlchemy для создания объектов Session.

Functions:
    init_db: Инициализирует базу данных, создавая все необходимые таблицы.
    get_db: Контекстный менеджер для работы с сессией базы данных.
    check_connection: Проверяет соединение с базой данных.
"""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine  # type: ignore
from sqlalchemy.exc import SQLAlchemyError  # type: ignore
from sqlalchemy.orm import Session, sessionmaker  # type: ignore

from app.config.settings import DATABASE_URL
from app.core.models import Base
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Создаем движок базы данных
engine = create_engine(
    DATABASE_URL,
    pool_size=5,  # Максимальное количество соединений в пуле
    max_overflow=10,  # Максимальное количество соединений, которые могут быть созданы сверх pool_size
    pool_timeout=30,  # Время ожидания доступного соединения в секундах
    pool_recycle=1800,  # Переподключение через 30 минут для предотвращения разрыва соединения
)

# Создаем фабрику сессий
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """
    Инициализация базы данных.

    Создает все таблицы, определенные в моделях, если они не существуют.
    Использует метаданные из Base для определения схемы.

    Raises:
        SQLAlchemyError: Если возникла ошибка при создании таблиц.

    Examples:
        >>> init_db()
        # Логирует "База данных успешно инициализирована" при успешном выполнении
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

    Создает новую сессию и автоматически управляет транзакциями,
    выполняя commit при успешном выполнении или rollback при ошибке.
    Также гарантирует закрытие сессии после использования.

    Yields:
        Session: Сессия базы данных SQLAlchemy для выполнения операций.

    Raises:
        SQLAlchemyError: При возникновении ошибок в операциях с базой данных.

    Examples:
        >>> with get_db() as db:
        ...     car = Car(title="Toyota Camry", price_usd=15000)
        ...     db.add(car)
        # Автоматически выполняет db.commit() при выходе из блока
        # или db.rollback() при возникновении исключения
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

    Выполняет простой SQL-запрос для проверки доступности базы данных.
    Логирует результат проверки.

    Returns:
        bool: True если подключение успешно установлено, False в противном случае.

    Examples:
        >>> is_connected = check_connection()
        >>> if is_connected:
        ...     print("База данных доступна")
        ... else:
        ...     print("Ошибка подключения к базе данных")
    """
    try:
        with get_db() as db:
            db.execute("SELECT 1")
            logger.info("Подключение к базе данных успешно")
            return True
    except SQLAlchemyError as e:
        logger.error("Ошибка подключения к базе данных", exc_info=True)
        return False
