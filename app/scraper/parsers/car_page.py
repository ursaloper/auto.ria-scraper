"""
Парсер страницы карточки автомобиля AutoRia.
"""

import re
from typing import Dict, Any, Optional, List
from bs4 import BeautifulSoup

from app.scraper.base import BaseScraper
from app.utils.logger import get_logger
from app.scraper.browser.utils import random_sleep

logger = get_logger(__name__)


class CarPageParser(BaseScraper):
    """
    Парсер для извлечения подробной информации со страницы автомобиля.
    """

    def __init__(self, headless: bool = True):
        super().__init__(headless=headless)

    def _extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Извлечение заголовка объявления."""
        title_tag = soup.select_one("h1.head, h3.auto-content_title")
        return title_tag.text.strip() if title_tag else None

    def _extract_price_usd(self, soup: BeautifulSoup) -> Optional[int]:
        """Извлечение цены в USD."""
        price_tag = soup.select_one("div.price_value > strong")
        if price_tag:
            price_text = re.sub(r"[^\d]", "", price_tag.text)
            return int(price_text) if price_text else None
        return None

    def _extract_odometer(self, soup: BeautifulSoup) -> Optional[int]:
        """Извлечение пробега."""
        odometer_tag = soup.select_one(
            "div.base-information span.size18.thin, div.base-information span.size18"
        )
        if odometer_tag and "тис. км" in odometer_tag.text:
            odometer_text = re.sub(r"[^\d]", "", odometer_tag.text)
            return int(odometer_text) * 1000 if odometer_text else None
        elif odometer_tag:
            odometer_text = re.sub(r"[^\d]", "", odometer_tag.text)
            return int(odometer_text) if odometer_text else None
        return None

    def _extract_username(self, soup: BeautifulSoup) -> Optional[str]:
        """Извлечение имени продавца."""
        username_tag = soup.select_one("div.seller_info_name > a")
        if username_tag:
            return username_tag.text.strip()

        # Затем для частных продавцов
        username_tag = soup.select_one(
            "div.user-name > h4.seller_info_name, div.view-seller-info .seller_info_name"
        )
        if username_tag:
            return username_tag.text.strip()

        # Обобщенный поиск, если предыдущие не сработали
        username_tag = soup.select_one(".seller_info .seller_info_name")
        if username_tag:
            return username_tag.text.strip()
        return None

    def _normalize_phone(self, phone_text: str) -> str:
        """
        Нормализация телефонного номера в международный формат.

        Args:
            phone_text (str): Исходный текст с номером телефона

        Returns:
            str: Нормализованный номер в формате +380...
        """
        # Удаляем все, кроме цифр
        digits_only = re.sub(r"[^\d]", "", phone_text.replace("+", ""))

        # Проверяем, начинается ли номер с 0 (украинский формат)
        if digits_only.startswith("0") and len(digits_only) >= 10:
            # Заменяем первый 0 на 380 для украинских номеров
            return "+380" + digits_only[1:]

        # Если номер уже с кодом страны (например, начинается с 380)
        if digits_only.startswith("380") and len(digits_only) >= 12:
            return "+" + digits_only

        # В других случаях просто добавляем +
        return "+" + digits_only

    def _extract_phone_numbers(self, soup: BeautifulSoup) -> List[str]:
        """Извлечение номеров телефонов."""
        phone_numbers = []
        try:
            # Сначала закрываем cookie-баннер, если он есть
            if self.browser_manager.close_cookie_banner():
                logger.info("Cookie-баннер успешно закрыт")
                # Небольшая пауза после закрытия баннера
                random_sleep(1, 2)

            # Кликаем по кнопке показа телефона
            show_phone_selector = ".phone_show_link"
            if self.browser_manager.click(show_phone_selector):
                logger.debug(
                    f"Успешный клик по кнопке показа телефона: {show_phone_selector}"
                )
                # Увеличиваем время ожидания для полной загрузки номера
                random_sleep(2, 3)

                # Ждем появления блока с телефоном
                phone_selector = ".popup-successful-call-desk"
                if self.browser_manager.wait_for_selector(phone_selector, timeout=5000):
                    logger.debug("Блок с телефоном найден")

                    # Получаем атрибут data-value через JavaScript
                    try:
                        phone_value = self.browser_manager.page.evaluate(
                            """() => {
                            const phoneElement = document.querySelector('.popup-successful-call-desk');
                            return phoneElement ? (phoneElement.getAttribute('data-value') || phoneElement.textContent.trim()) : null;
                        }"""
                        )

                        if phone_value:
                            logger.info(
                                f"Найден телефон через JavaScript: {phone_value}"
                            )
                            normalized_phone = self._normalize_phone(phone_value)
                            if len(normalized_phone) > 7:
                                phone_numbers.append(normalized_phone)
                    except Exception as e:
                        logger.error(
                            f"Ошибка при получении телефона через JavaScript: {e}",
                            exc_info=True,
                        )

                # Обновляем soup после клика для поиска номера в HTML
                current_html = self.browser_manager.get_html()
                if current_html:
                    soup = self.get_soup(current_html)
            else:
                logger.warning("Не удалось кликнуть по кнопке показа телефона")

        except Exception as e:
            logger.error(f"Ошибка при извлечении телефона: {e}", exc_info=True)

        # Ищем телефон в HTML, если не нашли через JavaScript
        if not phone_numbers:
            # Селекторы для поиска телефонов в разных вариантах разметки
            phone_selectors = [
                ".popup-successful-call-desk",  # Основной селектор после клика
                'div[data-value^="("]',  # div с атрибутом data-value, начинающимся с (
                ".phones_item .phone",  # Классические селекторы
                '.seller_info_item [href^="tel:"]',  # Ссылки с tel:
                ".phone.bold",  # Дополнительный селектор
            ]

            for selector in phone_selectors:
                phone_tags = soup.select(selector)
                for tag in phone_tags:
                    # Пробуем извлечь телефон из data-value или из текста
                    if tag.has_attr("data-value"):
                        phone_text = tag["data-value"]
                    elif tag.has_attr("href") and tag["href"].startswith("tel:"):
                        phone_text = tag["href"].replace("tel:", "")
                    else:
                        phone_text = tag.text.strip()

                    if phone_text:
                        normalized_phone = self._normalize_phone(phone_text)
                        if len(normalized_phone) > 7:
                            phone_numbers.append(normalized_phone)

        if phone_numbers:
            logger.info(f"Найдены телефоны: {phone_numbers}")
        else:
            logger.warning("Телефоны не найдены")

        return list(set(phone_numbers))  # Возвращаем уникальные номера

    def _extract_image_url(self, soup: BeautifulSoup) -> Optional[str]:
        """
        Извлечение URL основного изображения.
        """
        # Ищем <img> внутри .photo-620x465 с классом outline m-auto
        img_tag = soup.select_one("div.photo-620x465 img.outline.m-auto[src]")
        if img_tag and img_tag.has_attr("src"):
            return img_tag["src"]
        # Fallback: ищем любой <img> внутри .photo-620x465
        img_tag = soup.select_one("div.photo-620x465 img[src]")
        if img_tag and img_tag.has_attr("src"):
            return img_tag["src"]
        return None

    def _extract_images_count(self, soup: BeautifulSoup) -> Optional[int]:
        """Извлечение количества изображений."""
        # Пробуем найти по тексту "Смотреть все N фотографий"
        a_tag = soup.find("a", class_="show-all")
        if a_tag and a_tag.text:
            import re

            match = re.search(r"все\s+(\d+)\s+фот", a_tag.text)
            if match:
                return int(match.group(1))
        return 1  # Если не нашли счетчик, но есть главное фото - ставим 1

    def _extract_car_number(self, soup: BeautifulSoup) -> Optional[str]:
        """Извлечение номера автомобиля."""
        number_tag = soup.select_one("span.state-num")
        if number_tag:
            # Берём только прямой текст, игнорируя вложенные popup-спаны
            direct_text = number_tag.find(text=True, recursive=False)
            if direct_text:
                car_number = direct_text.strip().replace(" ", "").upper()
                # Проверка: номер должен содержать буквы и цифры, и быть не слишком коротким
                if (
                    len(car_number) >= 6
                    and any(c.isalpha() for c in car_number)
                    and any(c.isdigit() for c in car_number)
                ):
                    return car_number
        return None

    def _extract_car_vin(self, soup: BeautifulSoup) -> Optional[str]:
        """Извлечение VIN-кода."""
        vin_tag = soup.select_one(
            "span.label-vin, span.vin-code, .vin-checked+.data-check .vin"
        )
        return vin_tag.text.strip() if vin_tag else None

    def parse_car_page(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Парсинг одной страницы автомобиля.

        Args:
            url (str): URL страницы автомобиля.

        Returns:
            Optional[Dict[str, Any]]: Словарь с данными об автомобиле или None при ошибке.
        """
        logger.info(f"Парсинг страницы автомобиля: {url}")
        html = self.get_page_source(url)
        if not html:
            logger.error(f"Не удалось получить HTML для URL: {url}")
            return None

        soup = self.get_soup(html)

        # Ожидание загрузки ключевых элементов
        if not self.wait_for_selector(
            "div.price_value, h1.head, .ticket-status-0", timeout=20000
        ):
            logger.warning(
                f"Ключевые элементы на странице {url} не загрузились вовремя."
            )

        data = {
            "url": url,
            "title": self._extract_title(soup),
            "price_usd": self._extract_price_usd(soup),
            "odometer": self._extract_odometer(soup),
            "username": self._extract_username(soup),
            "phone_numbers": [],  # Будет заполнено ниже, после возможного клика
            "image_url": self._extract_image_url(soup),
            "images_count": None,  # Будет определено после image_url
            "car_number": self._extract_car_number(soup),
            "car_vin": self._extract_car_vin(soup),
        }

        # Извлечение телефонов (может потребовать клика)
        data["phone_numbers"] = self._extract_phone_numbers(soup)

        # Обновление количества изображений после получения основного URL
        images_count = self._extract_images_count(soup)
        if images_count:
            data["images_count"] = images_count
        elif data["image_url"]:
            data["images_count"] = 1  # Если есть главное фото, но нет счетчика
        else:
            data["images_count"] = 0

        # Проверка на наличие основных данных
        if not data["title"] or not data["price_usd"]:
            logger.error(
                f"Не удалось извлечь заголовок или цену для {url}. Данные: {data}"
            )

        logger.info(f"Успешно извлечены данные для {url}")
        return data

    def parse(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Основной метод для парсинга страницы автомобиля.

        Args:
            url (str): URL страницы автомобиля.

        Returns:
            Optional[Dict[str, Any]]: Словарь с данными или None.
        """
        with self:
            return self.parse_car_page(url)


# Пример использования (для тестирования)
if __name__ == "__main__":
    test_url = "https://auto.ria.com/auto_audi_q7_38309788.html"
    parser = CarPageParser(headless=False)  # False для видимого браузера
    car_data = parser.parse(test_url)

    if car_data:
        logger.info("Извлеченные данные:")
        for key, value in car_data.items():
            logger.info(f"{key}: {value}")
    else:
        logger.info("Не удалось извлечь данные.")
