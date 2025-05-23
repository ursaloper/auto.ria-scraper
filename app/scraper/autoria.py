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

from app.config.settings import (
    MAX_CARS_TO_PROCESS,
    MAX_PAGES_TO_PARSE,
    SCRAPER_CONCURRENCY,
    SCRAPER_START_URL,
)
from app.core.database import Session, get_db
from app.scraper.parsers.car_page import CarPageParser
from app.scraper.parsers.search_page import SearchPageParser
from app.utils.db_utils import check_url_exists, check_urls_batch, safe_insert_car
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

        Использует безопасную вставку с блокировкой на уровне транзакции
        для предотвращения гонки условий при параллельной вставке.
        Преобразует списки телефонных номеров в строку с разделителями.

        Args:
            db (Session): Сессия базы данных SQLAlchemy.
            car_data (Dict[str, Any]): Словарь с данными автомобиля,
                собранными парсером страницы автомобиля.

        Returns:
            bool: True если сохранение успешно выполнено, False в случае ошибки.
        """
        if not car_data or not car_data.get("url"):
            logger.warning("Нет данных для сохранения или отсутствует URL")
            return False

        try:
            # Подготовка телефонных номеров
            phone_numbers_str = None
            if isinstance(car_data.get("phone_numbers"), list):
                phone_numbers_str = ", ".join(car_data["phone_numbers"])
            elif isinstance(car_data.get("phone_numbers"), str):
                phone_numbers_str = car_data["phone_numbers"]

            # Подготовка данных для вставки
            car_insert_data = {
                "url": car_data["url"],
                "title": car_data.get("title"),
                "price_usd": car_data.get("price_usd"),
                "odometer": car_data.get("odometer") or 0,
                "username": car_data.get("username"),
                "phone_number": phone_numbers_str,
                "image_url": car_data.get("image_url"),
                "images_count": car_data.get("images_count"),
                "car_number": car_data.get("car_number"),
                "car_vin": car_data.get("car_vin"),
                "datetime_found": datetime.now(),
            }

            # Безопасная вставка с блокировкой
            car_id = safe_insert_car(db, car_insert_data)

            return car_id is not None
        except Exception as e:
            logger.error(
                f"Ошибка при сохранении автомобиля {car_data.get('url')}: {str(e)}",
                exc_info=True,
            )
            return False

    async def _process_car_page(
        self, car_url: str, client: httpx.AsyncClient, db: Session, attempt: int = 1
    ) -> Optional[Dict[str, Any]]:
        """
        Обработка страницы автомобиля с повторными попытками при ошибках.

        Сначала проверяет, существует ли запись с данным URL в базе данных,
        и только затем выполняет запрос к странице автомобиля.

        Args:
            car_url (str): URL-адрес страницы автомобиля.
            client (httpx.AsyncClient): HTTP-клиент для выполнения запросов.
            db (Session): Сессия базы данных SQLAlchemy.
            attempt (int, optional): Номер текущей попытки. По умолчанию 1.

        Returns:
            Optional[Dict[str, Any]]: Словарь с данными автомобиля или None при ошибке.

        Note:
            При ошибке функция пытается повторить запрос до self.retry_count раз
            с задержкой self.retry_delay секунд между попытками.
        """
        # Сначала проверяем, есть ли запись с таким URL в базе данных
        car_id = check_url_exists(db, car_url)
        if car_id:
            logger.info(f"Автомобиль с URL {car_url} уже существует в БД, ID: {car_id}")
            return None

        try:
            async with self._error_handler("парсинге страницы автомобиля", car_url):
                return await self.car_parser.parse(car_url, client=client)
        except Exception as e:
            if attempt < self.retry_count:
                logger.warning(
                    f"Попытка {attempt} не удалась для {car_url}. Повторная попытка через {self.retry_delay} сек."
                )
                await asyncio.sleep(self.retry_delay)
                return await self._process_car_page(car_url, client, db, attempt + 1)
            return None

    async def run(self) -> Dict[str, int]:
        """
        Запуск процесса скрапинга.

        Основной метод, который выполняет полный цикл скрапинга:
        1. Собирает ссылки на автомобили с страниц поиска
        2. Проверяет, какие ссылки уже обработаны (есть в БД)
        3. Обрабатывает каждую новую страницу автомобиля параллельно сразу после получения ссылок
        4. Сохраняет данные в базу данных

        Returns:
            Dict[str, int]: Статистика процесса скрапинга с ключами:
                - processed (int): Количество обработанных автомобилей
                - saved (int): Количество сохраненных в базу данных автомобилей
                - skipped (int): Количество пропущенных автомобилей (уже в БД)

        Note:
            Метод использует ограничение на количество одновременных запросов
            через asyncio.Semaphore для предотвращения перегрузки сервера.
        """
        logger.info(f"Запуск скрапера AutoRia. URL: {self.start_url}")
        processed_count = saved_count = skipped_count = 0
        car_links_total = []
        sem = asyncio.Semaphore(SCRAPER_CONCURRENCY)  # Ограничение параллелизма

        # Функция для обработки одного автомобиля
        async def process_car(car_url, client, db):
            nonlocal processed_count, saved_count
            async with sem:
                car_details = await self._process_car_page(car_url, client, db)
                processed_count += 1
                if car_details and self._save_car_data(db, car_details):
                    saved_count += 1

        try:
            async with self._error_handler("сборе ссылок", self.start_url):
                async with httpx.AsyncClient(
                    headers={"User-Agent": self.ua.random}
                ) as client:
                    logger.info(f"Начинаем сбор ссылок с {self.start_url}")

                    # Все задачи обработки автомобилей
                    car_tasks = []

                    with get_db() as db:
                        # Счетчик для отслеживания общего количества обрабатываемых URL (включая пропущенные)
                        total_urls_count = 0
                        # Счетчик страниц
                        page_count = 0
                        current_url = self.start_url

                        # Список URL, которые уже есть в БД (для оптимизации)
                        existing_urls = set()

                        # Обрабатываем каждую страницу поиска
                        while current_url:
                            if MAX_PAGES_TO_PARSE and page_count >= MAX_PAGES_TO_PARSE:
                                logger.info(
                                    f"Достигнут лимит в {MAX_PAGES_TO_PARSE} страниц."
                                )
                                break

                            # Парсим страницу поиска
                            page_data = await self.search_parser.parse_page(
                                current_url, client
                            )
                            car_links = page_data["car_links"]
                            next_url = page_data["next_page_url"]

                            logger.info(
                                f"Найдено {len(car_links)} ссылок на странице {page_count}."
                            )

                            # Проверяем на дубликаты перед добавлением в общий список
                            new_links = []
                            for link in car_links:
                                if link not in car_links_total:
                                    new_links.append(link)
                                    car_links_total.append(link)

                            logger.info(
                                f"Добавлено {len(new_links)} новых уникальных ссылок (отфильтровано {len(car_links) - len(new_links)} дубликатов)."
                            )

                            # Пакетная проверка URL в базе данных
                            batch_urls_to_check = [
                                url for url in new_links if url not in existing_urls
                            ]
                            if batch_urls_to_check:
                                batch_existing = check_urls_batch(
                                    db, batch_urls_to_check
                                )
                                existing_urls.update(batch_existing.keys())
                                skipped_count += len(batch_existing)
                                logger.info(
                                    f"Найдено {len(batch_existing)} URL, которые уже есть в БД"
                                )

                            # Статистика по текущему состоянию
                            logger.info(
                                f"Статистика: всего URL: {total_urls_count}, пропущено: {skipped_count}, "
                                f"задач создано: {len(car_tasks)}, лимит: {MAX_CARS_TO_PROCESS or 'не установлен'}"
                            )

                            # Запускаем обработку только новых автомобилей с текущей страницы
                            for car_url in new_links:
                                # Увеличиваем общий счетчик URL
                                total_urls_count += 1

                                # Проверяем лимит на общее количество URL
                                if (
                                    MAX_CARS_TO_PROCESS
                                    and total_urls_count > MAX_CARS_TO_PROCESS
                                ):
                                    logger.info(
                                        f"Достигнут лимит в {MAX_CARS_TO_PROCESS} URL (обработано + пропущено)."
                                    )
                                    break

                                # Пропускаем URL, которые уже есть в БД
                                if car_url in existing_urls:
                                    logger.debug(
                                        f"Пропускаем {car_url} - уже есть в БД"
                                    )
                                    continue

                                #logger.info(
                                #    f"Обработка {len(car_tasks)+1}/{MAX_CARS_TO_PROCESS or 'неограничено'}: {car_url}"
                                #)
                                task = asyncio.create_task(
                                    process_car(car_url, client, db)
                                )
                                car_tasks.append(task)

                            # Проверяем, не достигли ли мы лимита
                            if (
                                MAX_CARS_TO_PROCESS
                                and total_urls_count >= MAX_CARS_TO_PROCESS
                            ):
                                logger.info(
                                    f"Достигнут лимит в {MAX_CARS_TO_PROCESS} URL (обработано + пропущено)."
                                )
                                break

                            # Переходим на следующую страницу, если она есть
                            if next_url:
                                current_url = next_url
                                page_count += 1
                                await asyncio.sleep(1)  # Пауза между страницами
                            else:
                                logger.info("Достигнута последняя страница поиска.")
                                break

                        # Ожидаем завершения всех задач обработки автомобилей
                        if car_tasks:
                            await asyncio.gather(*car_tasks)

            logger.info(
                f"Скрапинг завершен. Обработано страниц: {page_count}. Всего ссылок: {len(car_links_total)}. "
                f"Пропущено (уже в БД): {skipped_count}. Обработано авто: {processed_count}, сохранено: {saved_count}"
            )
            return {
                "processed": processed_count,
                "saved": saved_count,
                "skipped": skipped_count,
            }
        except Exception as e:
            logger.critical(
                f"Критическая ошибка в процессе скрапинга: {str(e)}", exc_info=True
            )
            return {
                "processed": processed_count,
                "saved": saved_count,
                "skipped": skipped_count,
            }


# Для ручного запуска
if __name__ == "__main__":
    scraper = AutoRiaScraper()
    asyncio.run(scraper.run())
