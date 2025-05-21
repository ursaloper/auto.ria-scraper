"""
Модуль для управления браузером через Playwright.
"""

from typing import Optional, Any
from playwright.sync_api import sync_playwright, Browser, Page, Playwright  # type: ignore
from fake_useragent import UserAgent  # type: ignore

from app.utils.logger import get_logger

logger = get_logger(__name__)


class BrowserManager:
    """Менеджер для работы с Playwright."""

    def __init__(self, headless: bool = True):
        """
        Инициализация менеджера.

        Args:
            headless (bool): Запускать браузер в фоновом режиме
        """
        self.headless = headless
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.user_agent = UserAgent().random

    def _setup_browser_args(self) -> list[str]:
        """Настройка аргументов запуска браузера."""
        return [
            "--disable-dev-shm-usage",  # Важно для Docker
            "--no-sandbox",  # Для работы в Docker
            "--disable-setuid-sandbox",
            "--disable-gpu",  # Отключаем GPU
            "--disable-notifications",  # Отключаем уведомления
            "--disable-popup-blocking",  # Отключаем блокировку всплывающих окон
            f"--user-agent={self.user_agent}",  # Устанавливаем случайный User-Agent
        ]

    def start(self) -> None:
        """Запуск браузера."""
        try:
            logger.info("Инициализация Playwright...")
            self.playwright = sync_playwright().start()

            browser_args = self._setup_browser_args()
            self.browser = self.playwright.chromium.launch(
                headless=self.headless, args=browser_args
            )

            self.page = self.browser.new_page()
            self.page.set_viewport_size({"width": 1920, "height": 1080})
            self.page.set_default_timeout(30000)  # 30 секунд таймаут

            # Настройка перехватчиков для оптимизации
            self.page.route("**/*.{png,jpg,jpeg,gif,svg}", lambda route: route.abort())
            self.page.route("**/*.{css,less,scss}", lambda route: route.abort())
            self.page.route(
                "**/*.{woff,woff2,ttf,otf,eot}", lambda route: route.abort()
            )

            logger.info("Playwright успешно инициализирован")
        except Exception as e:
            logger.error("Ошибка при инициализации Playwright", exc_info=True)
            self.stop()
            raise

    def stop(self) -> None:
        """Остановка браузера."""
        try:
            if self.page:
                self.page.close()
                self.page = None

            if self.browser:
                self.browser.close()
                self.browser = None

            if self.playwright:
                self.playwright.stop()
                self.playwright = None

            logger.info("Playwright успешно остановлен")
        except Exception as e:
            logger.error("Ошибка при остановке Playwright", exc_info=True)

    def get_page(self, url: str) -> bool:
        """
        Загрузка страницы.

        Args:
            url (str): URL страницы

        Returns:
            bool: True если страница загружена успешно, False в противном случае
        """
        if not self.page:
            logger.error("Браузер не инициализирован")
            return False

        try:
            logger.info(f"Загрузка страницы: {url}")
            self.page.goto(url, wait_until="networkidle")
            return True
        except Exception as e:
            logger.error(f"Ошибка при загрузке страницы {url}", exc_info=True)
            return False

    def wait_for_selector(self, selector: str, timeout: int = 30000) -> Any:
        """
        Ожидание появления элемента на странице.

        Args:
            selector (str): CSS селектор
            timeout (int): Время ожидания в миллисекундах

        Returns:
            Any: Элемент если найден, None в противном случае
        """
        try:
            return self.page.wait_for_selector(selector, timeout=timeout)
        except Exception as e:
            logger.warning(f"Элемент не найден: {selector}")
            return None

    def click(self, selector: str, timeout: int = 30000) -> bool:
        """
        Клик по элементу.

        Args:
            selector (str): CSS селектор
            timeout (int): Время ожидания в миллисекундах

        Returns:
            bool: True если клик выполнен успешно, False в противном случае
        """
        try:
            element = self.wait_for_selector(selector, timeout)
            if element:
                element.click()
                return True
            return False
        except Exception as e:
            logger.error(f"Ошибка при клике на элемент: {selector}", exc_info=True)
            return False

    def get_text(self, selector: str, timeout: int = 30000) -> Optional[str]:
        """
        Получение текста элемента.

        Args:
            selector (str): CSS селектор
            timeout (int): Время ожидания в миллисекундах

        Returns:
            Optional[str]: Текст элемента или None
        """
        try:
            element = self.wait_for_selector(selector, timeout)
            return element.text_content().strip() if element else None
        except Exception as e:
            logger.error(
                f"Ошибка при получении текста элемента: {selector}", exc_info=True
            )
            return None

    def get_html(self) -> Optional[str]:
        """
        Получение HTML-кода страницы.

        Returns:
            Optional[str]: HTML-код страницы или None
        """
        try:
            return self.page.content() if self.page else None
        except Exception as e:
            logger.error("Ошибка при получении HTML", exc_info=True)
            return None

    def close_cookie_banner(self) -> bool:
        """
        Закрытие cookie-баннера, если он присутствует на странице.

        Returns:
            bool: True если баннер был закрыт, False в противном случае
        """
        try:
            # Проверяем наличие cookie-баннера
            banner_selector = ".fc-consent-root"
            if not self.page.query_selector(banner_selector):
                logger.debug("Cookie-баннер не обнаружен")
                return False

            logger.info("Обнаружен cookie-баннер, пытаемся закрыть...")

            # Пробуем различные селекторы для кнопки согласия
            consent_selectors = [
                ".fc-button.fc-cta-consent",  # Основная кнопка согласия
                ".fc-cta-consent",  # Упрощенный селектор
                ".fc-footer-buttons-container button",  # Любая кнопка в футере
                "#fc-button-agree",  # ID кнопки согласия
            ]

            for selector in consent_selectors:
                try:
                    if self.page.query_selector(selector):
                        self.page.click(selector, timeout=5000)
                        logger.info(f"Cookie-баннер закрыт (селектор: {selector})")
                        return True
                except Exception:
                    continue

            # Пробуем закрыть через JavaScript
            try:
                logger.debug("Попытка закрыть cookie-баннер через JavaScript")
                self.page.evaluate(
                    """() => {
                    const elements = document.querySelectorAll('.fc-button.fc-cta-consent, .fc-cta-consent, .fc-footer-buttons-container button');
                    if (elements.length > 0) {
                        elements[0].click();
                        return true;
                    }
                    return false;
                }"""
                )
                return True
            except Exception:
                pass

            # Пробуем удалить баннер из DOM
            try:
                logger.debug("Попытка удалить cookie-баннер из DOM")
                self.page.evaluate(
                    """() => {
                    const banner = document.querySelector('.fc-consent-root');
                    if (banner) {
                        banner.remove();
                        return true;
                    }
                    return false;
                }"""
                )
                return True
            except Exception:
                pass

            logger.warning("Не удалось закрыть cookie-баннер")
            return False
        except Exception as e:
            logger.error(f"Ошибка при закрытии cookie-баннера: {e}", exc_info=True)
            return False

    def __enter__(self):
        """Контекстный менеджер - запуск."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Контекстный менеджер - остановка."""
        self.stop()
