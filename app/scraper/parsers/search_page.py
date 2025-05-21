"""
Парсер страницы поиска AutoRia.
"""

from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from app.scraper.base import BaseScraper
from app.utils.logger import get_logger
from app.config.settings import SCRAPER_START_URL
from app.scraper.browser.utils import scroll_to_bottom, random_sleep

logger = get_logger(__name__)


class SearchPageParser(BaseScraper):
    """
    Парсер для извлечения данных со страницы поиска AutoRia.
    Извлекает ссылки на карточки автомобилей и информацию для пагинации.
    """

    def __init__(self, headless: bool = True):
        super().__init__(headless=headless)
        self.current_page = 1

    def _extract_car_links(self, soup: BeautifulSoup) -> List[str]:
        """Извлечение ссылок на страницы автомобилей."""
        car_links = []
        ticket_items = soup.select("section.ticket-item")

        for item in ticket_items:
            link_tag = item.select_one("a.m-link-ticket")
            if link_tag and link_tag.has_attr("href"):
                car_links.append(link_tag["href"])

        logger.info(
            f"Найдено {len(car_links)} ссылок на автомобили на странице {self.current_page}"
        )
        return car_links

    def _get_next_page_url(self, soup: BeautifulSoup) -> Optional[str]:
        """Получение URL следующей страницы пагинации."""
        next_page_tag = soup.select_one("a.page-link.js-next")
        if next_page_tag and next_page_tag.has_attr("href"):
            href = next_page_tag["href"]
            # Преобразуем относительный путь в абсолютный
            return urljoin("https://auto.ria.com", href)
        return None

    def parse_page(self, url: str) -> Dict[str, Any]:
        """
        Парсинг одной страницы поиска.

        Args:
            url (str): URL страницы поиска

        Returns:
            Dict[str, Any]: Словарь с ссылками на автомобили и URL следующей страницы.
                           {'car_links': [...], 'next_page_url': '...'}
        """
        logger.info(f"Парсинг страницы поиска: {url}")
        html = self.get_page_source(url)
        if not html:
            logger.error(f"Не удалось получить HTML для URL: {url}")
            return {"car_links": [], "next_page_url": None}

        soup = self.get_soup(html)

        # Ожидание загрузки основного контента
        if not self.wait_for_selector("section.ticket-item", timeout=20000):
            logger.warning(f"Контент на странице {url} не загрузился вовремя.")
            # Пробуем прокрутку страницы
            if self.page:
                scroll_to_bottom(self.page)
                random_sleep(2, 3)
                html = self.browser_manager.get_html()
                if html:
                    soup = self.get_soup(html)
                    if not soup.select("section.ticket-item"):
                        logger.error(
                            f"Автомобили на странице {url} так и не найдены после прокрутки."
                        )
                        return {"car_links": [], "next_page_url": None}

        car_links = self._extract_car_links(soup)
        next_page_url = self._get_next_page_url(soup)

        return {"car_links": car_links, "next_page_url": next_page_url}

    def parse(
        self, start_url: str = SCRAPER_START_URL, max_pages: Optional[int] = None
    ) -> List[str]:
        """
        Парсинг всех страниц поиска, начиная с указанной.

        Args:
            start_url (str): Начальный URL для парсинга.
            max_pages (Optional[int]): Максимальное количество страниц для парсинга.

        Returns:
            List[str]: Список всех найденных ссылок на автомобили.
        """
        all_car_links = []
        current_url: Optional[str] = start_url
        self.current_page = 1

        with self:
            while current_url:
                if max_pages and self.current_page > max_pages:
                    logger.info(f"Достигнут лимит в {max_pages} страниц.")
                    break

                page_data = self.parse_page(current_url)
                all_car_links.extend(page_data["car_links"])

                current_url = page_data["next_page_url"]
                if current_url:
                    logger.info(f"Переход на следующую страницу: {current_url}")
                    self.current_page += 1
                    random_sleep(1, 2)  # Пауза между страницами
                else:
                    logger.info("Достигнута последняя страница поиска.")
                    break

        logger.info(f"Всего найдено {len(all_car_links)} ссылок на автомобили.")
        return all_car_links


# Пример использования (для тестирования)
if __name__ == "__main__":
    parser = SearchPageParser(headless=False)  # False для видимого браузера
    links = parser.parse(max_pages=2)  # Парсим не более 2 страниц для теста

    if links:
        logger.info(f"Первые 5 найденных ссылок:")
        for link in links[:5]:
            logger.info(link)
    else:
        logger.info("Ссылки не найдены.")
