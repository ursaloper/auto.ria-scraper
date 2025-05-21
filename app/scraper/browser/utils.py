"""
Утилиты для работы с Playwright.
"""

import time
import random
from typing import Optional
from playwright.sync_api import Page

from app.utils.logger import get_logger

logger = get_logger(__name__)


def scroll_to_bottom(page: Page, scroll_pause: float = 1.0) -> None:
    """
    Прокрутка страницы до конца.

    Args:
        page (Page): Экземпляр страницы Playwright
        scroll_pause (float): Пауза между прокрутками в секундах
    """
    try:
        last_height = page.evaluate("document.body.scrollHeight")

        while True:
            # Прокрутка вниз
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

            # Пауза для загрузки контента
            time.sleep(scroll_pause + random.uniform(0.1, 0.5))

            # Проверка новой высоты
            new_height = page.evaluate("document.body.scrollHeight")
            if new_height == last_height:
                break

            last_height = new_height

    except Exception as e:
        logger.error("Ошибка при прокрутке страницы", exc_info=True)


def wait_and_get_text(page: Page, selector: str, timeout: int = 30000) -> Optional[str]:
    """
    Ожидание и получение текста элемента.

    Args:
        page (Page): Экземпляр страницы Playwright
        selector (str): CSS селектор
        timeout (int): Время ожидания в миллисекундах

    Returns:
        Optional[str]: Текст элемента или None в случае ошибки
    """
    try:
        element = page.wait_for_selector(selector, timeout=timeout)
        return element.text_content().strip() if element else None
    except Exception as e:
        logger.warning(f"Элемент не найден: {selector}")
        return None


def safe_click(page: Page, selector: str, timeout: int = 30000) -> bool:
    """
    Безопасный клик по элементу с ожиданием.

    Args:
        page (Page): Экземпляр страницы Playwright
        selector (str): CSS селектор
        timeout (int): Время ожидания в миллисекундах

    Returns:
        bool: True если клик выполнен успешно, False в противном случае
    """
    try:
        element = page.wait_for_selector(selector, timeout=timeout)
        if element:
            element.click()
            return True
        return False
    except Exception as e:
        logger.error(f"Ошибка при клике на элемент: {selector}", exc_info=True)
        return False


def random_sleep(min_seconds: float = 1.0, max_seconds: float = 3.0) -> None:
    """
    Случайная пауза между запросами.

    Args:
        min_seconds (float): Минимальное время паузы
        max_seconds (float): Максимальное время паузы
    """
    time.sleep(random.uniform(min_seconds, max_seconds))
