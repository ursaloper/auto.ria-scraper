"""
Base asynchronous parser class.

This module provides an abstract base class for all parsers in the project.
Defines common interface and basic functionality that should be implemented
by all specialized parsers.

Attributes:
    logger: Logger for registering parsing events.

Classes:
    BaseScraper: Abstract base class for all parsers.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict

from bs4 import BeautifulSoup

from app.utils.logger import get_logger

logger = get_logger(__name__)


class BaseScraper(ABC):
    """
    Base class for asynchronous parsers.

    Defines common interface and basic functionality for all parsers.
    Inheritors must implement the parse() method to extract data
    from specific types of pages.

    Methods:
        get_soup: Creates BeautifulSoup object from HTML code.
        parse: Abstract method for parsing data, must be implemented in inheritors.
    """

    @staticmethod
    def get_soup(html: str) -> BeautifulSoup:
        """
        Create BeautifulSoup object from HTML.

        Converts HTML code into BeautifulSoup data structure for subsequent
        parsing and information extraction. Uses lxml parser for better
        performance and reliability.

        Args:
            html (str): Page HTML code for parsing.

        Returns:
            BeautifulSoup: BeautifulSoup object for convenient HTML parsing.

        Examples:
            >>> html = "<html><body><h1>Title</h1></body></html>"
            >>> soup = BaseScraper.get_soup(html)
            >>> soup.h1.text
            'Title'
        """
        return BeautifulSoup(html, "lxml")

    @abstractmethod
    async def parse(self, *args, **kwargs) -> Dict[str, Any]:
        """
        Abstract asynchronous parsing method.

        Must be implemented in child classes to extract
        data from specific types of pages.

        Args:
            *args: Positional arguments specific to the concrete parser.
            **kwargs: Named arguments specific to the concrete parser.

        Returns:
            Dict[str, Any]: Dictionary with extracted data.

        Raises:
            NotImplementedError: If method is not overridden in child class.
        """
        pass
