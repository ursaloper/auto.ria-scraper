"""
Парсер страницы поиска auto.ria.com (асинхронный, httpx+bs4).

Этот модуль реализует асинхронный парсер для извлечения списка ссылок на автомобили
с страниц поиска auto.ria.com. Использует httpx для HTTP-запросов и BeautifulSoup для
парсинга HTML. Поддерживает пагинацию и ограничение количества обрабатываемых страниц.

Attributes:
    logger: Логгер для регистрации событий парсинга.
    SCRAPER_START_URL: URL-адрес начальной страницы для скрапинга (из настроек).

Classes:
    SearchPageParser: Парсер для страниц поиска auto.ria.com.
"""

import asyncio
import random
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import httpx  # type: ignore
from bs4 import BeautifulSoup

from app.config.settings import SCRAPER_START_URL
from app.scraper.base import BaseScraper
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SearchPageParser(BaseScraper):
    """
    Асинхронный парсер для извлечения данных со страницы поиска AutoRia.

    Извлекает ссылки на страницы автомобилей с страниц результатов поиска.
    Поддерживает пагинацию для обработки многостраничных результатов поиска.

    Attributes:
        current_page (int): Текущий номер страницы поиска (начиная с 0).
        base_url (str): Базовый URL сайта AutoRia.
    """

    def __init__(self):
        """
        Инициализация парсера страниц поиска.

        Устанавливает начальные значения для счетчика страниц и базового URL.
        """
        self.current_page = 0  # Начинаем с page=0
        self.base_url = "https://auto.ria.com"

    def _extract_car_links(self, soup: BeautifulSoup) -> List[str]:
        """
        Извлечение ссылок на страницы автомобилей.

        Находит и извлекает ссылки на страницы с детальной информацией
        об автомобилях из HTML-кода страницы поиска.

        Args:
            soup (BeautifulSoup): Объект BeautifulSoup с HTML-кодом страницы поиска.

        Returns:
            List[str]: Список URL-адресов страниц автомобилей.
        """
        car_links = []
        ticket_items = soup.select("section.ticket-item")
        for item in ticket_items:
            link_tag = item.select_one("a.m-link-ticket")
            if link_tag and link_tag.has_attr("href"):
                car_links.append(link_tag["href"])

        page_str = (
            f"на странице {self.current_page}"
            if self.current_page > 0
            else "на первой странице"
        )
        logger.info(f"Найдено {len(car_links)} ссылок на автомобили {page_str}")
        return car_links

    def _get_next_page_url(self, current_url: str) -> str:
        """
        Генерирует URL следующей страницы путем увеличения параметра page.

        Анализирует текущий URL, увеличивает номер страницы в параметре page
        и формирует новый URL для следующей страницы результатов поиска.

        Args:
            current_url (str): URL текущей страницы поиска.

        Returns:
            str: URL следующей страницы поиска.

        Note:
            Просто увеличивает номер страницы на 1, независимо от общего количества страниц.
        """
        # Парсим текущий URL
        parsed_url = urlparse(current_url)
        query_params = parse_qs(parsed_url.query)

        # Определяем текущий номер страницы из URL
        current_page_num = 0
        if "page" in query_params and query_params["page"]:
            try:
                current_page_num = int(query_params["page"][0])
            except (ValueError, IndexError):
                current_page_num = 0

        # Увеличиваем номер страницы на 1
        next_page = current_page_num + 1
        query_params["page"] = [str(next_page)]

        # Собираем новый URL
        new_query = urlencode(query_params, doseq=True)
        next_url_parts = list(parsed_url)
        next_url_parts[4] = new_query
        next_url = urlunparse(next_url_parts)
        logger.info(f"Сгенерирован URL для страницы {next_page}: {next_url}")
        return next_url

    async def parse_page(self, url: str, client: httpx.AsyncClient) -> Dict[str, Any]:
        """
        Парсинг одной страницы поиска.

        Выполняет HTTP-запрос к указанному URL, извлекает ссылки на автомобили
        и формирует URL для следующей страницы поиска.

        Args:
            url (str): URL страницы поиска для парсинга.
            client (httpx.AsyncClient): HTTP-клиент для выполнения запросов.

        Returns:
            Dict[str, Any]: Словарь с результатами парсинга, содержащий:
                - car_links (List[str]): Список ссылок на страницы автомобилей.
                - next_page_url (Optional[str]): URL следующей страницы или None,
                  если ссылки не найдены (конец списка).

        Raises:
            Exception: Перехватывает и логирует все исключения при запросе HTML.
        """
        # Обновляем текущую страницу на основе URL
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        if "page" in query_params and query_params["page"]:
            try:
                self.current_page = int(query_params["page"][0])
            except (ValueError, IndexError):
                self.current_page = 0

        logger.info(f"Парсинг страницы поиска: {url} (страница {self.current_page})")
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                resp = await client.get(url)
                resp.raise_for_status()
                html = resp.text
                break
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 503 and retry_count < max_retries - 1:
                    retry_count += 1
                    wait_time = (
                        5 + random.randint(1, 5) * retry_count
                    )  # Увеличиваем время ожидания с каждой попыткой
                    logger.warning(
                        f"Получен статус 503 для {url}. Повторная попытка {retry_count}/{max_retries} через {wait_time} сек."
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Не удалось получить HTML для URL: {url}: {e}")
                    return {"car_links": [], "next_page_url": None}
            except Exception as e:
                logger.error(f"Не удалось получить HTML для URL: {url}: {e}")
                return {"car_links": [], "next_page_url": None}
        else:
            # Если все попытки исчерпаны
            logger.error(f"Исчерпаны все попытки получения HTML для URL: {url}")
            return {"car_links": [], "next_page_url": None}

        soup = self.get_soup(html)
        car_links = self._extract_car_links(soup)

        # Если на странице нет объявлений, считаем что достигли конца
        if not car_links:
            logger.info(
                f"На странице {self.current_page} не найдено объявлений. Достигнут конец списка."
            )
            return {"car_links": [], "next_page_url": None}

        # Всегда генерируем URL следующей страницы
        next_page_url = self._get_next_page_url(url)
        return {"car_links": car_links, "next_page_url": next_page_url}

    async def parse(
        self,
        start_url: str = SCRAPER_START_URL,
        max_pages: Optional[int] = None,
        max_cars: Optional[int] = None,
        client: Optional[httpx.AsyncClient] = None,
    ) -> List[str]:
        """
        Основной метод для парсинга страниц поиска AutoRia.

        Выполняет последовательный парсинг страниц поиска, начиная с указанного URL,
        и собирает ссылки на страницы автомобилей. Поддерживает ограничение по
        количеству страниц и общему количеству собираемых ссылок.

        Args:
            start_url (str, optional): URL начальной страницы поиска.
                По умолчанию используется URL из настроек приложения.
            max_pages (Optional[int], optional): Максимальное количество страниц для парсинга.
                None означает отсутствие ограничения.
            max_cars (Optional[int], optional): Максимальное количество ссылок на автомобили.
                None означает отсутствие ограничения.
            client (Optional[httpx.AsyncClient], optional): HTTP-клиент для выполнения запросов.
                Если не указан, создается новый клиент, который закрывается после использования.

        Returns:
            List[str]: Список URL-адресов страниц автомобилей.

        Note:
            Метод делает паузу в 1 секунду между запросами к страницам поиска.
        """
        all_car_links = []
        current_url: Optional[str] = start_url
        pages_processed = 0  # Счетчик обработанных страниц
        close_client = False
        if client is None:
            client = httpx.AsyncClient()
            close_client = True
        try:
            while current_url:
                # Проверяем лимит страниц
                if max_pages and pages_processed >= max_pages:
                    logger.info(f"Достигнут лимит в {max_pages} страниц.")
                    break

                page_data = await self.parse_page(current_url, client)
                all_car_links.extend(page_data["car_links"])
                next_url = page_data["next_page_url"]

                # Увеличиваем счетчик обработанных страниц
                pages_processed += 1

                if next_url:
                    logger.info(f"Переход на следующую страницу: {next_url}")
                    current_url = next_url
                    await asyncio.sleep(1)  # Пауза между страницами
                else:
                    logger.info("Достигнута последняя страница поиска.")
                    break
        finally:
            if close_client:
                await client.aclose()

        # Ограничиваем общее количество ссылок, если max_cars задан
        if max_cars:
            all_car_links = all_car_links[:max_cars]
            logger.info(
                f"Ограничено {len(all_car_links)} ссылок на автомобили по max_cars={max_cars}"
            )

        logger.info(f"Всего найдено {len(all_car_links)} ссылок на автомобили.")
        return all_car_links


# Пример использования (для тестирования)
if __name__ == "__main__":
    parser = SearchPageParser()
    links = parser.parse(max_pages=2)  # Парсим не более 2 страниц для теста

    if links:
        logger.info(f"Первые 5 найденных ссылок:")
        for link in links[:5]:
            logger.info(link)
    else:
        logger.info("Ссылки не найдены.")
