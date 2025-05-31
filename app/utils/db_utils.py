"""
Database utilities.

This module contains helper functions for working with the database,
including checking for existing records, optimized queries and other operations.
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
    Checks if a record with the specified URL exists in the database.

    Args:
        db (Session): SQLAlchemy database session.
        url (str): URL to check.

    Returns:
        Optional[int]: Record ID if URL exists in database, or None if record not found.

    Example:
        ```python
        with get_db() as db:
            car_id = check_url_exists(db, "https://auto.ria.com/auto_bmw_x5_12345.html")
            if car_id:
                logger.info(f"Car with URL already exists in DB, ID: {car_id}")
        ```
    """
    try:
        # Use .scalar() instead of .first() for optimization - we only need ID
        result = db.query(Car.id).filter(Car.url == url).scalar()
        return result
    except Exception as e:
        logger.error(f"Error checking URL in database: {str(e)}", exc_info=True)
        return None


def check_urls_batch(db: Session, urls: list[str]) -> dict[str, int]:
    """
    Checks if records with specified URLs exist in database (batch check).

    Args:
        db (Session): SQLAlchemy database session.
        urls (list[str]): List of URLs to check.

    Returns:
        dict[str, int]: Dictionary {url: id} for found URLs.

    Example:
        ```python
        with get_db() as db:
            urls_to_check = ["https://auto.ria.com/auto_bmw_x5_12345.html", "https://auto.ria.com/auto_audi_a4_54321.html"]
            existing_urls = check_urls_batch(db, urls_to_check)
            for url, car_id in existing_urls.items():
                logger.info(f"Car with URL {url} already exists in DB, ID: {car_id}")
        ```
    """
    try:
        # Batch query to get all URLs that already exist in DB
        results = db.query(Car.url, Car.id).filter(Car.url.in_(urls)).all()
        return {url: car_id for url, car_id in results}
    except Exception as e:
        logger.error(
            f"Error during batch URL check in database: {str(e)}", exc_info=True
        )
        return {}


def safe_insert_car(db: Session, car_data: Dict[str, Any]) -> Optional[int]:
    """
    Safely inserts new car record into database with duplicate check.

    Uses transaction-level locking to prevent race conditions
    when inserting same URLs or VINs by different threads in parallel.

    Args:
        db (Session): SQLAlchemy database session.
        car_data (Dict[str, Any]): Car data for insertion.

    Returns:
        Optional[int]: ID of inserted record or None if insertion failed.

    Example:
        ```python
        with get_db() as db:
            car_id = safe_insert_car(db, {
                "url": "https://auto.ria.com/auto_bmw_x5_12345.html",
                "title": "BMW X5 2020",
                "car_vin": "WBAKV210X00R12345",
                # ... other fields ...
            })
            if car_id:
                logger.info(f"Car successfully saved, ID: {car_id}")
        ```
    """
    if not car_data or not car_data.get("url"):
        logger.warning("No data to save or URL missing")
        return None

    url = car_data["url"]
    vin = car_data.get("car_vin")

    try:
        # Start transaction
        db.begin_nested()

        try:
            # Lock table to prevent race conditions
            db.execute(text("LOCK TABLE cars IN SHARE ROW EXCLUSIVE MODE"))

            # Check if record with this URL already exists
            existing_id = db.query(Car.id).filter(Car.url == url).scalar()
            if existing_id:
                logger.info(
                    f"Car with URL {url} already exists in DB, ID: {existing_id}"
                )
                db.commit()
                return None

            # If VIN is specified, check if record with this VIN already exists
            if vin:
                existing_id_by_vin = (
                    db.query(Car.id).filter(Car.car_vin == vin).scalar()
                )
                if existing_id_by_vin:
                    logger.info(
                        f"Car with VIN {vin} already exists in DB, ID: {existing_id_by_vin}"
                    )
                    db.commit()
                    return None

            # Create new record
            new_car = Car(**car_data)
            db.add(new_car)
            db.commit()

            logger.info(
                f"Car {car_data.get('title')} successfully saved, ID: {new_car.id}"
            )
            return new_car.id
        except Exception as e:
            db.rollback()
            raise e

    except IntegrityError as e:
        # Check if record was added by another process
        existing_id = db.query(Car.id).filter(Car.url == url).scalar()
        if existing_id:
            logger.info(
                f"Car with URL {url} was added by another process, ID: {existing_id}"
            )
            return None

        # Check if there was VIN violation
        if vin:
            existing_id_by_vin = db.query(Car.id).filter(Car.car_vin == vin).scalar()
            if existing_id_by_vin:
                logger.info(
                    f"Car with VIN {vin} was added by another process, ID: {existing_id_by_vin}"
                )
                return None

        logger.error(
            f"Integrity error when saving car {url}: {str(e)}",
            exc_info=True,
        )
        return None
    except Exception as e:
        logger.error(f"Error saving car {url}: {str(e)}", exc_info=True)
        return None
