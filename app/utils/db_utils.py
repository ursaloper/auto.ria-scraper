"""
Утилиты для работы с базой данных.

Этот модуль содержит вспомогательные функции для работы с базой данных,
включая проверку наличия записей, оптимизированные запросы и другие операции.
"""

from typing import Any, Dict, Optional

from sqlalchemy import text  # type: ignore
from sqlalchemy.exc import IntegrityError  # type: ignore

from app.core.database import Session
from app.core.models import Car
from app.utils.logger import get_logger

logger = get_logger(__name__)


def check_url_exists(db: Session, url: str) -> Optional[int]:
    """
    Проверяет, существует ли запись с указанным URL в базе данных.

    Args:
        db (Session): Сессия базы данных SQLAlchemy.
        url (str): URL для проверки.

    Returns:
        Optional[int]: ID записи, если URL существует в базе данных, или None, если запись не найдена.

    Example:
        ```python
        with get_db() as db:
            car_id = check_url_exists(db, "https://auto.ria.com/auto_bmw_x5_12345.html")
            if car_id:
                logger.info(f"Автомобиль с URL уже существует в БД, ID: {car_id}")
        ```
    """
    try:
        # Используем .scalar() вместо .first() для оптимизации - нам нужен только ID
        result = db.query(Car.id).filter(Car.url == url).scalar()
        return result
    except Exception as e:
        logger.error(f"Ошибка при проверке URL в базе данных: {str(e)}", exc_info=True)
        return None


def check_urls_batch(db: Session, urls: list[str]) -> dict[str, int]:
    """
    Проверяет, существуют ли записи с указанными URL в базе данных (пакетная проверка).

    Args:
        db (Session): Сессия базы данных SQLAlchemy.
        urls (list[str]): Список URL для проверки.

    Returns:
        dict[str, int]: Словарь {url: id} для найденных URL.

    Example:
        ```python
        with get_db() as db:
            urls_to_check = ["https://auto.ria.com/auto_bmw_x5_12345.html", "https://auto.ria.com/auto_audi_a4_54321.html"]
            existing_urls = check_urls_batch(db, urls_to_check)
            for url, car_id in existing_urls.items():
                logger.info(f"Автомобиль с URL {url} уже существует в БД, ID: {car_id}")
        ```
    """
    try:
        # Пакетный запрос для получения всех URL, которые уже существуют в БД
        results = db.query(Car.url, Car.id).filter(Car.url.in_(urls)).all()
        return {url: car_id for url, car_id in results}
    except Exception as e:
        logger.error(
            f"Ошибка при пакетной проверке URL в базе данных: {str(e)}", exc_info=True
        )
        return {}


def safe_insert_car(db: Session, car_data: Dict[str, Any]) -> Optional[int]:
    """
    Безопасно вставляет новую запись автомобиля в базу данных с проверкой на дубликаты.

    Использует блокировку на уровне транзакции для предотвращения гонки условий
    при параллельной вставке одинаковых URL или VIN разными потоками.

    Args:
        db (Session): Сессия базы данных SQLAlchemy.
        car_data (Dict[str, Any]): Данные автомобиля для вставки.

    Returns:
        Optional[int]: ID вставленной записи или None, если вставка не удалась.

    Example:
        ```python
        with get_db() as db:
            car_id = safe_insert_car(db, {
                "url": "https://auto.ria.com/auto_bmw_x5_12345.html",
                "title": "BMW X5 2020",
                "car_vin": "WBAKV210X00R12345",
                # ... другие поля ...
            })
            if car_id:
                logger.info(f"Автомобиль успешно сохранен, ID: {car_id}")
        ```
    """
    if not car_data or not car_data.get("url"):
        logger.warning("Нет данных для сохранения или отсутствует URL")
        return None

    url = car_data["url"]
    vin = car_data.get("car_vin")

    try:
        # Начинаем транзакцию
        db.begin_nested()

        try:
            # Блокируем таблицу для предотвращения гонки условий
            db.execute(text("LOCK TABLE cars IN SHARE ROW EXCLUSIVE MODE"))

            # Проверяем, существует ли уже запись с таким URL
            existing_id = db.query(Car.id).filter(Car.url == url).scalar()
            if existing_id:
                logger.info(
                    f"Автомобиль с URL {url} уже существует в БД, ID: {existing_id}"
                )
                db.commit()
                return None

            # Если указан VIN, проверяем, существует ли уже запись с таким VIN
            if vin:
                existing_id_by_vin = (
                    db.query(Car.id).filter(Car.car_vin == vin).scalar()
                )
                if existing_id_by_vin:
                    logger.info(
                        f"Автомобиль с VIN {vin} уже существует в БД, ID: {existing_id_by_vin}"
                    )
                    db.commit()
                    return None

            # Создаем новую запись
            new_car = Car(**car_data)
            db.add(new_car)
            db.commit()

            logger.info(
                f"Автомобиль {car_data.get('title')} успешно сохранен, ID: {new_car.id}"
            )
            return new_car.id
        except Exception as e:
            db.rollback()
            raise e

    except IntegrityError as e:
        # Проверяем, не была ли запись добавлена другим процессом
        existing_id = db.query(Car.id).filter(Car.url == url).scalar()
        if existing_id:
            logger.info(
                f"Автомобиль с URL {url} был добавлен другим процессом, ID: {existing_id}"
            )
            return None

        # Проверяем, не было ли нарушение по VIN
        if vin:
            existing_id_by_vin = db.query(Car.id).filter(Car.car_vin == vin).scalar()
            if existing_id_by_vin:
                logger.info(
                    f"Автомобиль с VIN {vin} был добавлен другим процессом, ID: {existing_id_by_vin}"
                )
                return None

        logger.error(
            f"Ошибка целостности при сохранении автомобиля {url}: {str(e)}",
            exc_info=True,
        )
        return None
    except Exception as e:
        logger.error(f"Ошибка при сохранении автомобиля {url}: {str(e)}", exc_info=True)
        return None
