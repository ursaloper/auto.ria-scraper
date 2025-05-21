"""
Основной класс скрапера для сайта Auto.ria.com.
Использует Playwright для эффективного сбора данных.
"""

from typing import Dict, Any, Optional
from datetime import datetime
import time
from contextlib import contextmanager

from app.core.database import get_db, Session
from app.core.models import Car
from app.scraper.parsers.search_page import SearchPageParser
from app.scraper.parsers.car_page import CarPageParser
from app.config.settings import (
    SCRAPER_START_URL,
    MAX_PAGES_TO_PARSE,
    MAX_CARS_TO_PROCESS,
)
from app.utils.logger import get_logger
from app.scraper.browser.utils import random_sleep

logger = get_logger(__name__)


class AutoRiaScraper:
    """
    Основной скрапер для Auto.ria.com.
    Использует SearchPageParser для получения списка URL автомобилей
    и CarPageParser для парсинга каждой страницы автомобиля.
    Сохраняет данные в базу данных.
    """

    def __init__(self, start_url: str = SCRAPER_START_URL, headless: bool = True):
        """
        Инициализация скрапера.

        Args:
            start_url (str): Начальный URL для парсинга
            headless (bool): Запускать браузер в фоновом режиме
        """
        self.start_url = start_url
        self.headless = headless
        self.search_parser = SearchPageParser(headless=self.headless)
        self.car_parser = CarPageParser(headless=self.headless)
        self.retry_count = 3
        self.retry_delay = 5

    @contextmanager
    def _error_handler(self, operation: str, url: str):
        """
        Контекстный менеджер для обработки ошибок.

        Args:
            operation (str): Название операции
            url (str): URL, с которым работаем
        """
        try:
            yield
        except Exception as e:
            logger.error(f"Ошибка при {operation} ({url}): {str(e)}", exc_info=True)
            raise

    def _save_car_data(self, db: Session, car_data: Dict[str, Any]) -> bool:
        """
        Сохранение данных об автомобиле в базу данных.
        Проверяет на дубликаты по URL.

        Args:
            db (Session): Сессия базы данных
            car_data (Dict[str, Any]): Данные автомобиля

        Returns:
            bool: True если сохранение успешно, False в противном случае
        """
        if not car_data or not car_data.get("url"):
            logger.warning("Нет данных для сохранения или отсутствует URL")
            return False

        try:
            # Проверка на дубликаты
            existing_car = db.query(Car).filter(Car.url == car_data["url"]).first()
            if existing_car:
                logger.info(f"Автомобиль с URL {car_data['url']} уже существует в БД")
                return False

            # Подготовка телефонных номеров
            phone_numbers_str = None
            if isinstance(car_data.get("phone_numbers"), list):
                phone_numbers_str = ", ".join(car_data["phone_numbers"])
            elif isinstance(car_data.get("phone_numbers"), str):
                phone_numbers_str = car_data["phone_numbers"]

            # Создание и сохранение записи
            new_car = Car(
                url=car_data["url"],
                title=car_data.get("title"),
                price_usd=car_data.get("price_usd"),
                odometer=car_data.get("odometer"),
                username=car_data.get("username"),
                phone_number=phone_numbers_str,
                image_url=car_data.get("image_url"),
                images_count=car_data.get("images_count"),
                car_number=car_data.get("car_number"),
                car_vin=car_data.get("car_vin"),
                datetime_found=datetime.now(),
            )
            db.add(new_car)
            db.commit()

            logger.info(f"Автомобиль {car_data['title']} успешно сохранен")
            return True

        except Exception as e:
            db.rollback()
            logger.error(
                f"Ошибка при сохранении автомобиля {car_data.get('url')}: {str(e)}",
                exc_info=True,
            )
            return False

    def _process_car_page(
        self, car_url: str, attempt: int = 1
    ) -> Optional[Dict[str, Any]]:
        """
        Обработка страницы автомобиля с поддержкой повторных попыток.

        Args:
            car_url (str): URL страницы автомобиля
            attempt (int): Номер текущей попытки

        Returns:
            Optional[Dict[str, Any]]: Данные автомобиля или None при ошибке
        """
        try:
            with self._error_handler("парсинге страницы автомобиля", car_url):
                return self.car_parser.parse(car_url)
        except Exception as e:
            if attempt < self.retry_count:
                logger.warning(
                    f"Попытка {attempt} не удалась для {car_url}. Повторная попытка через {self.retry_delay} сек."
                )
                time.sleep(self.retry_delay)
                return self._process_car_page(car_url, attempt + 1)
            return None

    def run(self) -> Dict[str, int]:
        """
        Запускает процесс скрапинга.
        Возвращает статистику обработки.
        """
        logger.info(f"Запуск скрапера AutoRia. URL: {self.start_url}")

        try:
            # Сбор ссылок на автомобили
            with self._error_handler("сборе ссылок", self.start_url):
                car_links = self.search_parser.parse(
                    start_url=self.start_url, max_pages=MAX_PAGES_TO_PARSE
                )

            if not car_links:
                logger.warning("Не найдено ссылок на автомобили")
                return {
                    "processed": 0,
                    "saved": 0
                }

            logger.info(f"Собрано {len(car_links)} ссылок")

            processed_count = saved_count = 0

            with get_db() as db:
                for i, car_url in enumerate(car_links, 1):
                    if MAX_CARS_TO_PROCESS and processed_count >= MAX_CARS_TO_PROCESS:
                        logger.info(
                            f"Достигнут лимит в {MAX_CARS_TO_PROCESS} автомобилей"
                        )
                        break

                    logger.info(f"Обработка {i}/{len(car_links)}: {car_url}")

                    car_details = self._process_car_page(car_url)
                    processed_count += 1

                    if car_details and self._save_car_data(db, car_details):
                        saved_count += 1

                    # Пауза между запросами
                    random_sleep(1, 3)

            logger.info(
                f"Скрапинг завершен. Обработано: {processed_count}, сохранено: {saved_count}"
            )

            return {
                "processed": processed_count,
                "saved": saved_count
            }

        except Exception as e:
            logger.critical(
                f"Критическая ошибка в процессе скрапинга: {str(e)}", exc_info=True
            )
            return {
                "processed": 0,
                "saved": 0
            }
        finally:
            # Гарантируем закрытие браузеров
            try:
                self.search_parser.browser_manager.stop()
                self.car_parser.browser_manager.stop()
            except Exception as e:
                logger.error(f"Ошибка при закрытии браузеров: {str(e)}")


if __name__ == "__main__":
    scraper = AutoRiaScraper(headless=True)
    scraper.run()
