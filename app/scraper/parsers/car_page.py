"""
Auto.ria.com car page parser (asynchronous, httpx+bs4).

This module implements an asynchronous parser for extracting detailed car information
from ad pages on the auto.ria.com website. The module uses httpx
for HTTP requests and BeautifulSoup for HTML parsing. A feature of the module is
two-stage data collection: first, basic information is extracted from the HTML page,
then a separate XHR request is made to get the seller's phone number.

Attributes:
    logger: Logger for registering parsing events.
    ua: Random User-Agent header generator.

Classes:
    CarPageParser: Parser for pages with detailed car information.
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
    Asynchronous parser for extracting detailed information from car page.

    This class is responsible for collecting all car data from the ad page,
    including title, price, mileage, seller contact information, VIN code
    and license plate information. Implements a two-stage approach: first collects basic
    information from HTML, then makes XHR request to get seller's phone.

    Attributes:
        No explicit class attributes initialized in __init__.

    Methods:
        parse: Main method for parsing car page.
        _extract_*: Helper methods for extracting specific data.
        _fetch_phone: Method for making XHR request to API to get seller's phone.
        _normalize_phone: Method for normalizing phone number.
        _is_deleted_listing: Method for checking if listing is deleted.
    """

    def _extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract ad title."""
        title_tag = soup.select_one("h1.head, h3.auto-content_title")
        return title_tag.text.strip() if title_tag else None

    def _extract_price_usd(self, soup: BeautifulSoup) -> Optional[int]:
        """Extract price in USD."""
        price_tag = soup.select_one("div.price_value > strong")
        if price_tag:
            price_text = re.sub(r"[^\d]", "", price_tag.text)
            return int(price_text) if price_text else None
        return None

    def _extract_odometer(self, soup: BeautifulSoup) -> Optional[int]:
        """Extract mileage."""
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
        """Extract seller name."""
        # New selector for professional sellers
        username_tag = soup.select_one("a.sellerPro")
        if username_tag:
            return username_tag.text.strip()

        # Private sellers
        username_tag = soup.select_one("div.seller_info_name > a")
        if username_tag:
            return username_tag.text.strip()

        username_tag = soup.select_one(
            "div.user-name > h4.seller_info_name, div.view-seller-info .seller_info_name"
        )
        if username_tag:
            return username_tag.text.strip()

        # General search if previous ones didn't work
        username_tag = soup.select_one(".seller_info .seller_info_name")
        if username_tag:
            return username_tag.text.strip()

        # <div class="seller_info_name grey bold">Name not specified</div>
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

        # Check if listing is deleted - in this case username may be missing
        if self._is_deleted_listing(soup):
            logger.info("Username not found - listing deleted")
        else:
            logger.error("Failed to extract username (seller name) from car page")

        return None

    def _normalize_phone(self, phone_text: str) -> str:
        """
        Normalize phone number to international format.

        Args:
            phone_text (str): Original text with phone number

        Returns:
            str: Normalized number in +380... format
        """
        # Remove everything except digits
        digits_only = re.sub(r"[^\d]", "", phone_text.replace("+", ""))

        # Check if number starts with 0 (Ukrainian format)
        if digits_only.startswith("0") and len(digits_only) >= 10:
            # Replace first 0 with 380 for Ukrainian numbers
            return "+380" + digits_only[1:]

        # If number already has country code (e.g., starts with 380)
        if digits_only.startswith("380") and len(digits_only) >= 12:
            return "+" + digits_only

        # In other cases just add +
        return "+" + digits_only

    def _extract_image_url(self, soup: BeautifulSoup) -> Optional[str]:
        """
        Extract main image URL.
        """
        # Look for <img> inside .photo-620x465 with class outline m-auto
        img_tag = soup.select_one("div.photo-620x465 img.outline.m-auto[src]")
        if img_tag and img_tag.has_attr("src"):
            return img_tag["src"]
        # Fallback: look for any <img> inside .photo-620x465
        img_tag = soup.select_one("div.photo-620x465 img[src]")
        if img_tag and img_tag.has_attr("src"):
            return img_tag["src"]
        return None

    def _extract_images_count(self, soup: BeautifulSoup) -> Optional[int]:
        """Extract number of images."""
        # Try to find by text "View all N photos"
        a_tag = soup.find("a", class_="show-all")
        if a_tag and a_tag.text:
            import re

            match = re.search(r"все\s+(\d+)\s+фот", a_tag.text)
            if match:
                return int(match.group(1))
        return 1  # If didn't find counter but main photo exists - set 1

    def _extract_car_number(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract car license plate number."""
        number_tag = soup.select_one("span.state-num")
        if number_tag:
            # Take only direct text, ignoring nested popup spans
            direct_text = number_tag.find(text=True, recursive=False)
            if direct_text:
                car_number = direct_text.strip().replace(" ", "").upper()
                # Check: number should contain letters and digits, and not be too short
                if (
                    len(car_number) >= 6
                    and any(c.isalpha() for c in car_number)
                    and any(c.isdigit() for c in car_number)
                ):
                    return car_number
        return None

    def _extract_car_vin(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract VIN code."""
        vin_tag = soup.select_one(
            "span.label-vin, span.vin-code, .vin-checked+.data-check .vin"
        )
        return vin_tag.text.strip() if vin_tag else None

    def _is_deleted_listing(self, soup: BeautifulSoup) -> bool:
        """
        Check if listing is deleted.

        Args:
            soup (BeautifulSoup): BeautifulSoup object with page HTML

        Returns:
            bool: True if listing is deleted, False otherwise
        """
        # Check for deletion notification block
        deleted_block = soup.select_one(
            "div#autoDeletedTopBlock.notice.notice--icon.notice--orange"
        )
        if deleted_block:
            # Can also check text inside the block
            notice_text = deleted_block.text.strip()
            if "удалено и не принимает участия в поиске" in notice_text:
                logger.info(f"Found deleted listing: {notice_text}")
                return True
        return False

    async def _fetch_phone(
        self, soup: BeautifulSoup, url: str, client: httpx.AsyncClient, attempt: int = 1
    ) -> Optional[str]:
        MAX_RETRIES = 5
        # Look for car_id in url
        m = re.search(r"/auto_\w+_(\d+)\.html", url)
        car_id = m.group(1) if m else None
        if not car_id:
            logger.error(f"Failed to extract car_id from url: {url}")
            return None
        # Parse hash and expires from <script> or other elements with data-hash/data-expires
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
        # 2. If not found - look for any element with these data attributes
        if not hash_val or not expires:
            el = soup.find(attrs={"data-hash": True, "data-expires": True})
            if el:
                hash_val = el.get("data-hash")
                expires = el.get("data-expires")
        if not hash_val or not expires:
            logger.error(f"Failed to find hash/expires for phone on {url}")
            return None
        # Form XHR GET request
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
            await asyncio.sleep(random.uniform(2, 3))  # Pause after request
            if phone:
                logger.info(f"Phone successfully obtained via XHR GET: {phone}")
                return self._normalize_phone(phone)
        except HTTPStatusError as e:
            if e.response.status_code == 429:
                retry_after = e.response.headers.get("Retry-After")
                wait_time = (
                    int(retry_after) if retry_after and retry_after.isdigit() else 10
                )
                logger.warning(
                    f"429 Too Many Requests. Waiting {wait_time} sec before retry."
                )
                await asyncio.sleep(wait_time)
                if attempt < MAX_RETRIES:
                    return await self._fetch_phone(soup, url, client, attempt + 1)
                else:
                    logger.error(
                        f"Exceeded retry attempts for getting phone for {url}"
                    )
                    return None
            else:
                logger.error(f"Error during XHR GET request for phone: {e}", exc_info=True)
                await asyncio.sleep(random.uniform(2, 3))  # Pause after error
        except Exception as e:
            logger.error(f"Error during XHR GET request for phone: {e}", exc_info=True)
            await asyncio.sleep(random.uniform(2, 3))  # Pause after error
        logger.error(f"Failed to get phone for {url}")
        return None

    async def parse(
        self, url: str, client: Optional[httpx.AsyncClient] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Main method for parsing car page.

        Args:
            url (str): Car page URL.

        Returns:
            Optional[Dict[str, Any]]: Dictionary with data or None.
        """
        logger.info(f"Parsing car page: {url}")
        close_client = False
        if client is None:
            client = httpx.AsyncClient()
            close_client = True
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            html = resp.text
        except Exception as e:
            logger.error(f"Failed to get HTML for URL: {url}: {e}")
            if close_client:
                await client.aclose()
            return None

        soup = self.get_soup(html)

        # Check if listing is deleted
        if self._is_deleted_listing(soup):
            logger.warning(f"Listing deleted, skipping: {url}")
            if close_client:
                await client.aclose()
            return None

        # If username not found but listing not marked as deleted - continue parsing
        # In this case _extract_username may return None, and this will be handled later

        data = {
            "url": url,
            "title": self._extract_title(soup),
            "price_usd": self._extract_price_usd(soup),
            "odometer": self._extract_odometer(soup),
            "username": self._extract_username(soup),
            "phone_numbers": [],  # Will fill after XHR
            "image_url": self._extract_image_url(soup),
            "images_count": None,
            "car_number": self._extract_car_number(soup),
            "car_vin": self._extract_car_vin(soup),
        }
        # First all data, then phone
        phone = await self._fetch_phone(soup, url, client)
        if not phone:
            logger.error(f"Phone not obtained, car will not be saved: {url}")
            if close_client:
                await client.aclose()
            return None
        data["phone_numbers"] = [phone]
        
        # Number of photos
        data["images_count"] = self._extract_images_count(soup)

        # Check for presence of main data
        if not data["title"] or not data["price_usd"]:
            logger.error(
                f"Failed to extract title or price for {url}. Data: {data}"
            )
        logger.info(f"Successfully extracted data for {url}")
        if close_client:
            await client.aclose()
        return data


# Usage example (for testing)
if __name__ == "__main__":
    test_url = "https://auto.ria.com/auto_audi_q7_38309788.html"
    parser = CarPageParser()
    car_data = parser.parse(test_url)

    if car_data:
        logger.info("Extracted data:")
        for key, value in car_data.items():
            logger.info(f"{key}: {value}")
    else:
        logger.info("Failed to extract data.")
