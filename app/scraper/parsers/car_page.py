"""
Парсер страницы карточки автомобиля auto.ria.com (асинхронный, httpx+bs4).

Этот модуль реализует асинхронный парсер для извлечения подробной информации
об автомобиле с карточки объявления на сайте auto.ria.com. Модуль использует httpx
для HTTP-запросов и BeautifulSoup для парсинга HTML. Особенностью модуля является
двухэтапный сбор данных: сначала извлекается основная информация из HTML-страницы,
затем выполняется отдельный XHR-запрос для получения номера телефона продавца.

Attributes:
    logger: Логгер для регистрации событий парсинга.
    ua: Генератор случайных User-Agent заголовков.

Classes:
    CarPageParser: Парсер для страниц с детальной информацией об автомобиле.
"""

import asyncio
import random
import re
from typing import Any, Dict, List, Optional

import httpx  # type: ignore
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from httpx import HTTPStatusError  # type: ignore

from app.scraper.base import BaseScraper
from app.utils.logger import get_logger

logger = get_logger(__name__)

ua = UserAgent()


class CarPageParser(BaseScraper):
    """
    Асинхронный парсер для извлечения подробной информации со страницы автомобиля.

    Этот класс отвечает за сбор всех данных об автомобиле с страницы объявления,
    включая заголовок, цену, пробег, контактную информацию продавца, информацию
    о VIN-коде и госномере. Реализует двухэтапный подход: сначала собирает основную
    информацию из HTML, затем выполняет XHR-запрос для получения телефона продавца.

    Attributes:
        Нет явных атрибутов класса, инициализируемых в __init__.

    Methods:
        parse: Основной метод для парсинга страницы автомобиля.
        _extract_*: Вспомогательные методы для извлечения конкретных данных.
        _fetch_phone: Метод для выполнения XHR-запроса к API для получения телефона продавца.
        _normalize_phone: Метод для нормализации телефонного номера.
        _is_deleted_listing: Метод для проверки, является ли объявление удаленным.
    """

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
        # Новый селектор для профессиональных продавцов
        username_tag = soup.select_one("a.sellerPro")
        if username_tag:
            return username_tag.text.strip()

        # Частные продавцы
        username_tag = soup.select_one("div.seller_info_name > a")
        if username_tag:
            return username_tag.text.strip()

        username_tag = soup.select_one(
            "div.user-name > h4.seller_info_name, div.view-seller-info .seller_info_name"
        )
        if username_tag:
            return username_tag.text.strip()

        # Обобщенный поиск, если предыдущие не сработали
        username_tag = soup.select_one(".seller_info .seller_info_name")
        if username_tag:
            return username_tag.text.strip()

        # <div class="seller_info_name grey bold">Имя не указано</div>
        username_tag = soup.select_one("div.seller_info_name.grey.bold")
        if username_tag:
            return username_tag.text.strip()

        # <div class="seller_info_name bold">...</div>
        username_tag = soup.select_one("div.seller_info_name.bold")
        if username_tag:
            return username_tag.text.strip()

        # <h4 class="seller_info_name"> <a ...>...</a></h4>
        username_tag = soup.select_one("h4.seller_info_name > a")
        if username_tag:
            return username_tag.text.strip()

        # Проверяем, не удалено ли объявление - в этом случае username может отсутствовать
        if self._is_deleted_listing(soup):
            logger.info("Username не найден - объявление удалено")
        else:
            logger.error("Не удалось извлечь username (имя продавца) с карточки авто")

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

    def _is_deleted_listing(self, soup: BeautifulSoup) -> bool:
        """
        Проверяет, является ли объявление удаленным.

        Args:
            soup (BeautifulSoup): Объект BeautifulSoup с HTML страницы

        Returns:
            bool: True если объявление удалено, False в противном случае
        """
        # Проверяем наличие блока с уведомлением об удалении
        deleted_block = soup.select_one(
            "div#autoDeletedTopBlock.notice.notice--icon.notice--orange"
        )
        if deleted_block:
            # Можно также проверить текст внутри блока
            notice_text = deleted_block.text.strip()
            if "удалено и не принимает участия в поиске" in notice_text:
                logger.info(f"Найдено удаленное объявление: {notice_text}")
                return True
        return False

    async def _fetch_phone(
        self, soup: BeautifulSoup, url: str, client: httpx.AsyncClient, attempt: int = 1
    ) -> Optional[str]:
        MAX_RETRIES = 5
        # Ищем car_id в url
        m = re.search(r"/auto_\w+_(\d+)\.html", url)
        car_id = m.group(1) if m else None
        if not car_id:
            logger.error(f"Не удалось извлечь car_id из url: {url}")
            return None
        # Парсим hash и expires из <script> или других элементов с data-hash/data-expires
        hash_val = None
        expires = None
        # 1. <script ... data-hash=... data-expires=...>
        script_tag = soup.find(
            lambda tag: tag.name == "script"
            and tag.has_attr("data-hash")
            and tag.has_attr("data-expires")
        )
        if script_tag:
            hash_val = script_tag.get("data-hash")
            expires = script_tag.get("data-expires")
        # 2. Если не нашли — ищем любой элемент с этими data-атрибутами
        if not hash_val or not expires:
            el = soup.find(attrs={"data-hash": True, "data-expires": True})
            if el:
                hash_val = el.get("data-hash")
                expires = el.get("data-expires")
        if not hash_val or not expires:
            logger.error(f"Не удалось найти hash/expires для телефона на {url}")
            return None
        # Формируем XHR GET-запрос
        api_url = f"https://auto.ria.com/users/phones/{car_id}?hash={hash_val}&expires={expires}"
        headers = {
            "User-Agent": ua.random,
            "Referer": url,
            "Accept": "*/*",
        }
        try:
            resp = await client.get(api_url, headers=headers)
            resp.raise_for_status()
            json_data = resp.json()
            phone = None
            if "phones" in json_data and json_data["phones"]:
                phone = json_data["phones"][0].get("phoneFormatted")
            elif "formattedPhoneNumber" in json_data:
                phone = json_data["formattedPhoneNumber"]
            await asyncio.sleep(random.uniform(2, 3))  # Пауза после запроса
            if phone:
                logger.info(f"Телефон успешно получен через XHR GET: {phone}")
                return self._normalize_phone(phone)
        except HTTPStatusError as e:
            if e.response.status_code == 429:
                retry_after = e.response.headers.get("Retry-After")
                wait_time = (
                    int(retry_after) if retry_after and retry_after.isdigit() else 10
                )
                logger.warning(
                    f"429 Too Many Requests. Жду {wait_time} сек перед повтором."
                )
                await asyncio.sleep(wait_time)
                if attempt < MAX_RETRIES:
                    return await self._fetch_phone(soup, url, client, attempt + 1)
                else:
                    logger.error(
                        f"Превышено количество попыток получения телефона для {url}"
                    )
                    return None
            else:
                logger.error(f"Ошибка при XHR GET-запросе телефона: {e}", exc_info=True)
                await asyncio.sleep(random.uniform(2, 3))  # Пауза после ошибки
        except Exception as e:
            logger.error(f"Ошибка при XHR GET-запросе телефона: {e}", exc_info=True)
            await asyncio.sleep(random.uniform(2, 3))  # Пауза после ошибки
        logger.error(f"Не удалось получить телефон для {url}")
        return None

    async def parse(
        self, url: str, client: Optional[httpx.AsyncClient] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Основной метод для парсинга страницы автомобиля.

        Args:
            url (str): URL страницы автомобиля.

        Returns:
            Optional[Dict[str, Any]]: Словарь с данными или None.
        """
        logger.info(f"Парсинг страницы автомобиля: {url}")
        close_client = False
        if client is None:
            client = httpx.AsyncClient()
            close_client = True
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            html = resp.text
        except Exception as e:
            logger.error(f"Не удалось получить HTML для URL: {url}: {e}")
            if close_client:
                await client.aclose()
            return None

        soup = self.get_soup(html)

        # Проверяем, не удалено ли объявление
        if self._is_deleted_listing(soup):
            logger.warning(f"Объявление удалено, пропускаем: {url}")
            if close_client:
                await client.aclose()
            return None

        # Если username не найден, но объявление не помечено как удаленное - продолжаем парсинг
        # В таком случае _extract_username может вернуть None, и это будет обработано позже

        data = {
            "url": url,
            "title": self._extract_title(soup),
            "price_usd": self._extract_price_usd(soup),
            "odometer": self._extract_odometer(soup),
            "username": self._extract_username(soup),
            "phone_numbers": [],  # Заполним после XHR
            "image_url": self._extract_image_url(soup),
            "images_count": None,
            "car_number": self._extract_car_number(soup),
            "car_vin": self._extract_car_vin(soup),
        }
        # Сначала все данные, потом телефон
        phone = await self._fetch_phone(soup, url, client)
        if not phone:
            logger.error(f"Телефон не получен, авто не будет сохранено: {url}")
            if close_client:
                await client.aclose()
            return None
        data["phone_numbers"] = [phone]
        # Количество фото
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
        if close_client:
            await client.aclose()
        return data


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
