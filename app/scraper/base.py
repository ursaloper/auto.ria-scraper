"""
Базовый класс парсера.
"""

from typing import Optional, Dict, Any
from abc import ABC, abstractmethod
from bs4 import BeautifulSoup
from playwright.sync_api import Page

from app.utils.logger import get_logger
from app.scraper.browser.manager import BrowserManager

logger = get_logger(__name__)


class BaseScraper(ABC):
    """
    Базовый класс для парсеров.

    Attributes:
        browser_manager (BrowserManager): Менеджер браузера
        page (Page): Экземпляр страницы Playwright
    """

    def __init__(self, headless: bool = True):
        """
        Инициализация парсера.

        Args:
            headless (bool): Запускать браузер в фоновом режиме
        """
        self.browser_manager = BrowserManager(headless=headless)
        self.page: Optional[Page] = None

    def start(self) -> None:
        """Запуск парсера."""
        self.browser_manager.start()
        self.page = self.browser_manager.page

    def stop(self) -> None:
        """Остановка парсера."""
        self.browser_manager.stop()
        self.page = None

    def get_page_source(self, url: str) -> Optional[str]:
        """
        Получение HTML-кода страницы.

        Args:
            url (str): URL страницы

        Returns:
            Optional[str]: HTML-код страницы или None в случае ошибки
        """
        if not self.browser_manager.get_page(url):
            return None

        return self.browser_manager.get_html()

    def get_soup(self, html: str) -> BeautifulSoup:
        """
        Создание объекта BeautifulSoup из HTML.

        Args:
            html (str): HTML-код страницы

        Returns:
            BeautifulSoup: Объект для парсинга HTML
        """
        return BeautifulSoup(html, "lxml")

    def wait_for_selector(self, selector: str, timeout: int = 30000) -> bool:
        """
        Ожидание появления элемента на странице.

        Args:
            selector (str): CSS селектор
            timeout (int): Время ожидания в миллисекундах

        Returns:
            bool: True если элемент найден, False в противном случае
        """
        return bool(self.browser_manager.wait_for_selector(selector, timeout))

    @abstractmethod
    def parse(self, *args, **kwargs) -> Dict[str, Any]:
        """
        Абстрактный метод парсинга.
        Должен быть реализован в дочерних классах.
        """
        pass

    def __enter__(self):
        """Контекстный менеджер - запуск."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Контекстный менеджер - остановка."""
        self.stop()
