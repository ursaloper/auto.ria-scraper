"""
Базовый класс асинхронного парсера.

Этот модуль предоставляет абстрактный базовый класс для всех парсеров в проекте.
Определяет общий интерфейс и базовую функциональность, которую должны реализовывать
все специализированные парсеры.

Attributes:
    logger: Логгер для регистрации событий парсинга.

Classes:
    BaseScraper: Абстрактный базовый класс для всех парсеров.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict

from bs4 import BeautifulSoup

from app.utils.logger import get_logger

logger = get_logger(__name__)


class BaseScraper(ABC):
    """
    Базовый класс для асинхронных парсеров.

    Определяет общий интерфейс и базовую функциональность для всех парсеров.
    Наследники должны реализовать метод parse() для извлечения данных
    из конкретных типов страниц.

    Methods:
        get_soup: Создает объект BeautifulSoup из HTML-кода.
        parse: Абстрактный метод для парсинга данных, должен быть реализован в наследниках.
    """

    @staticmethod
    def get_soup(html: str) -> BeautifulSoup:
        """
        Создание объекта BeautifulSoup из HTML.

        Преобразует HTML-код в структуру данных BeautifulSoup для последующего
        парсинга и извлечения информации. Использует парсер lxml для лучшей
        производительности и надежности.

        Args:
            html (str): HTML-код страницы для парсинга.

        Returns:
            BeautifulSoup: Объект BeautifulSoup для удобного парсинга HTML.

        Examples:
            >>> html = "<html><body><h1>Заголовок</h1></body></html>"
            >>> soup = BaseScraper.get_soup(html)
            >>> soup.h1.text
            'Заголовок'
        """
        return BeautifulSoup(html, "lxml")

    @abstractmethod
    async def parse(self, *args, **kwargs) -> Dict[str, Any]:
        """
        Абстрактный асинхронный метод парсинга.

        Должен быть реализован в дочерних классах для извлечения
        данных из конкретных типов страниц.

        Args:
            *args: Позиционные аргументы, специфичные для конкретного парсера.
            **kwargs: Именованные аргументы, специфичные для конкретного парсера.

        Returns:
            Dict[str, Any]: Словарь с извлеченными данными.

        Raises:
            NotImplementedError: Если метод не переопределен в дочернем классе.
        """
        pass
