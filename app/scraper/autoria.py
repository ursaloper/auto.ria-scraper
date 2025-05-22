"""
Основной класс скрапера для сайта auto.ria.com (асинхронный, httpx+bs4).

Этот модуль реализует основной класс скрапера для сайта auto.ria.com, использующий
асинхронный подход с библиотекой httpx для HTTP-запросов и BeautifulSoup для
парсинга HTML. Скрапер собирает данные об автомобилях, включая информацию
о цене, пробеге, контактах продавца и другие характеристики.

Attributes:
    logger: Логгер для регистрации событий скрапинга.
    SCRAPER_START_URL: URL-адрес начальной страницы для скрапинга (из настроек).
    MAX_CARS_TO_PROCESS: Максимальное количество автомобилей для обработки (из настроек).
    MAX_PAGES_TO_PARSE: Максимальное количество страниц для парсинга (из настроек).
    SCRAPER_CONCURRENCY: Максимальное количество одновременных запросов (из настроек).

Classes:
    AutoRiaScraper: Основной класс для скрапинга данных с сайта auto.ria.com.
"""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, Optional

import httpx  # type: ignore
from fake_useragent import UserAgent

from app.config.settings import (MAX_CARS_TO_PROCESS, MAX_PAGES_TO_PARSE,
                                 SCRAPER_CONCURRENCY, SCRAPER_START_URL)
from app.core.database import Session, get_db
from app.core.models import Car
from app.scraper.parsers.car_page import CarPageParser
from app.scraper.parsers.search_page import SearchPageParser
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AutoRiaScraper:
    """
    Асинхронный скрапер для auto.ria.com.

    Этот класс реализует основную логику скрапинга данных с сайта auto.ria.com.
    Использует SearchPageParser для получения списка URL автомобилей
    и CarPageParser для парсинга каждой страницы автомобиля.
    Собранные данные сохраняются в базу данных PostgreSQL.

    Attributes:
        start_url (str): URL-адрес начальной страницы для скрапинга.
        search_parser (SearchPageParser): Парсер для страниц поиска.
        car_parser (CarPageParser): Парсер для страниц автомобилей.
        retry_count (int): Количество повторных попыток при ошибках.
        retry_delay (int): Задержка между повторными попытками в секундах.
        ua (UserAgent): Генератор случайных User-Agent заголовков.
    """

    def __init__(self, start_url: str = SCRAPER_START_URL):
        """
        Инициализация скрапера Auto.ria.com.

        Args:
            start_url (str, optional): URL-адрес начальной страницы для скрапинга.
                По умолчанию используется значение из настроек приложения.
        """
        self.start_url = start_url
        self.search_parser = SearchPageParser()
        self.car_parser = CarPageParser()
        self.retry_count = 3
        self.retry_delay = 5
        self.ua = UserAgent()

    @asynccontextmanager
    async def _error_handler(self, operation: str, url: str):
        """
        Асинхронный контекстный менеджер для обработки ошибок.

        Перехватывает и логирует исключения, возникающие при выполнении операций.

        Args:
            operation (str): Название выполняемой операции для логирования.
            url (str): URL-адрес, с которым связана операция.

        Yields:
            None: Просто предоставляет контекст выполнения.

        Raises:
            Exception: Перехватывает и логирует все исключения, затем повторно их вызывает.
        """
        try:
            yield
        except Exception as e:
            logger.error(f"Ошибка при {operation} ({url}): {str(e)}", exc_info=True)
            raise

    def _save_car_data(self, db: Session, car_data: Dict[str, Any]) -> bool:
        """
        Сохранение данных об автомобиле в базу данных.

        Проверяет на дубликаты по URL и сохраняет данные автомобиля в базу данных.
        Преобразует списки телефонных номеров в строку с разделителями.

        Args:
            db (Session): Сессия базы данных SQLAlchemy.
            car_data (Dict[str, Any]): Словарь с данными автомобиля,
                собранными парсером страницы автомобиля.

        Returns:
            bool: True если сохранение успешно выполнено, False в случае ошибки
                или если автомобиль с таким URL уже существует в базе данных.

        Raises:
            Exception: Перехватывает и логирует все исключения, затем возвращает False.
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

    async def _process_car_page(
        self, car_url: str, client: httpx.AsyncClient, attempt: int = 1
    ) -> Optional[Dict[str, Any]]:
        """
        Обработка страницы автомобиля с повторными попытками при ошибках.

        Вызывает парсер страницы автомобиля и повторяет попытки при ошибках.

        Args:
            car_url (str): URL-адрес страницы автомобиля.
            client (httpx.AsyncClient): HTTP-клиент для выполнения запросов.
            attempt (int, optional): Номер текущей попытки. По умолчанию 1.

        Returns:
            Optional[Dict[str, Any]]: Словарь с данными автомобиля или None при ошибке.

        Note:
            При ошибке функция пытается повторить запрос до self.retry_count раз
            с задержкой self.retry_delay секунд между попытками.
        """
        try:
            async with self._error_handler("парсинге страницы автомобиля", car_url):
                return await self.car_parser.parse(car_url, client=client)
        except Exception as e:
            if attempt < self.retry_count:
                logger.warning(
                    f"Попытка {attempt} не удалась для {car_url}. Повторная попытка через {self.retry_delay} сек."
                )
                await asyncio.sleep(self.retry_delay)
                return await self._process_car_page(car_url, client, attempt + 1)
            return None

    async def run(self) -> Dict[str, int]:
        """
        Запуск процесса скрапинга.

        Основной метод, который выполняет полный цикл скрапинга:
        1. Собирает ссылки на автомобили с страниц поиска
        2. Обрабатывает каждую страницу автомобиля
        3. Сохраняет данные в базу данных

        Returns:
            Dict[str, int]: Статистика процесса скрапинга с ключами:
                - processed (int): Количество обработанных автомобилей
                - saved (int): Количество сохраненных в базу данных автомобилей

        Note:
            Метод использует ограничение на количество одновременных запросов
            через asyncio.Semaphore для предотвращения перегрузки сервера.
        """
        logger.info(f"Запуск скрапера AutoRia. URL: {self.start_url}")
        try:
            async with self._error_handler("сборе ссылок", self.start_url):
                async with httpx.AsyncClient(
                    headers={"User-Agent": self.ua.random}
                ) as client:
                    logger.info(f"Начинаем сбор ссылок с {self.start_url}")
                    car_links = await self.search_parser.parse(
                        start_url=self.start_url,
                        max_pages=MAX_PAGES_TO_PARSE,
                        max_cars=MAX_CARS_TO_PROCESS,
                        client=client,
                    )
                    if not car_links:
                        logger.warning("Не найдено ссылок на автомобили")
                        return {"processed": 0, "saved": 0}

                    # Подробное логирование результатов сбора ссылок
                    logger.info(
                        f"Обработано страниц: {self.search_parser.current_page}"
                    )

                    logger.info(f"Собрано {len(car_links)} ссылок на автомобили")

                    # Если ссылок слишком мало - предупреждение
                    if len(car_links) < 10 and MAX_CARS_TO_PROCESS > 10:
                        logger.warning(
                            f"Собрано подозрительно мало ссылок: {len(car_links)}. Возможно, проблема с парсингом."
                        )

                    processed_count = saved_count = 0
                    sem = asyncio.Semaphore(
                        SCRAPER_CONCURRENCY
                    )  # Ограничение параллелизма
                    with get_db() as db:

                        async def process_and_save(car_url):
                            nonlocal processed_count, saved_count
                            async with sem:
                                car_details = await self._process_car_page(
                                    car_url, client
                                )
                                processed_count += 1
                                if car_details and self._save_car_data(db, car_details):
                                    saved_count += 1

                        tasks = []
                        for i, car_url in enumerate(car_links, 1):
                            logger.info(f"Обработка {i}/{len(car_links)}: {car_url}")
                            tasks.append(process_and_save(car_url))
                        await asyncio.gather(*tasks)
            logger.info(
                f"Скрапинг завершен. Обработано: {processed_count}, сохранено: {saved_count}"
            )
            return {"processed": processed_count, "saved": saved_count}
        except Exception as e:
            logger.critical(
                f"Критическая ошибка в процессе скрапинга: {str(e)}", exc_info=True
            )
            return {"processed": 0, "saved": 0}


# Для ручного запуска
if __name__ == "__main__":
    scraper = AutoRiaScraper()
    asyncio.run(scraper.run())
