"""
Main scraper class for auto.ria.com website (asynchronous, httpx+bs4).

This module implements the main scraper class for the auto.ria.com website, using
an asynchronous approach with httpx library for HTTP requests and BeautifulSoup for
HTML parsing. The scraper collects car data including information
about price, mileage, seller contacts and other characteristics.

Attributes:
    logger: Logger for registering scraping events.
    SCRAPER_START_URL: Starting page URL for scraping (from settings).
    MAX_CARS_TO_PROCESS: Maximum number of cars to process (from settings).
    MAX_PAGES_TO_PARSE: Maximum number of pages to parse (from settings).
    SCRAPER_CONCURRENCY: Maximum number of concurrent requests (from settings).

Classes:
    AutoRiaScraper: Main class for scraping data from auto.ria.com website.
"""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, Optional

import httpx  # type: ignore
from fake_useragent import UserAgent

from app.config.settings import (
    MAX_CARS_TO_PROCESS,
    MAX_PAGES_TO_PARSE,
    SCRAPER_CONCURRENCY,
    SCRAPER_START_URL,
)
from app.core.database import Session, get_db
from app.scraper.parsers.car_page import CarPageParser
from app.scraper.parsers.search_page import SearchPageParser
from app.utils.db_utils import check_url_exists, check_urls_batch, safe_insert_car
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AutoRiaScraper:
    """
    Asynchronous scraper for auto.ria.com.

    This class implements the main logic for scraping data from the auto.ria.com website.
    Uses SearchPageParser to get the list of car URLs
    and CarPageParser to parse each car page.
    Collected data is saved to PostgreSQL database.

    Attributes:
        start_url (str): Starting page URL for scraping.
        search_parser (SearchPageParser): Parser for search pages.
        car_parser (CarPageParser): Parser for car pages.
        retry_count (int): Number of retry attempts on errors.
        retry_delay (int): Delay between retry attempts in seconds.
        ua (UserAgent): Random User-Agent header generator.
    """

    def __init__(self, start_url: str = SCRAPER_START_URL):
        """
        Initialize Auto.ria.com scraper.

        Args:
            start_url (str, optional): Starting page URL for scraping.
                By default uses value from application settings.
        """
        self.start_url = start_url
        self.search_parser = SearchPageParser()
        self.car_parser = CarPageParser()
        self.retry_count = 3
        self.retry_delay = 5
        self.ua = UserAgent()

    @asynccontextmanager
    async def _error_handler(self, operation: str, url: str):
        """
        Asynchronous context manager for handling errors.

        Catches and logs exceptions that occur during operations.

        Args:
            operation (str): Name of the operation for logging.
            url (str): URL associated with the operation.

        Yields:
            None: Simply provides the execution context.

        Raises:
            Exception: Catches and logs all exceptions, then re-raises them.
        """
        try:
            yield
        except Exception as e:
            logger.error(f"Error during {operation} ({url}): {str(e)}", exc_info=True)
            raise

    def _save_car_data(self, db: Session, car_data: Dict[str, Any]) -> bool:
        """
        Save car data to database.

        Uses safe insert with transaction-level locking
        to prevent race conditions during parallel insertion.
        Converts phone number lists to string with delimiters.

        Args:
            db (Session): SQLAlchemy database session.
            car_data (Dict[str, Any]): Dictionary with car data
                collected by car page parser.

        Returns:
            bool: True if save was successful, False on error.
        """
        if not car_data or not car_data.get("url"):
            logger.warning("No data to save or URL missing")
            return False

        try:
            # Prepare phone numbers
            phone_numbers_str = None
            if isinstance(car_data.get("phone_numbers"), list):
                phone_numbers_str = ", ".join(car_data["phone_numbers"])
            elif isinstance(car_data.get("phone_numbers"), str):
                phone_numbers_str = car_data["phone_numbers"]

            # Prepare data for insertion
            car_insert_data = {
                "url": car_data["url"],
                "title": car_data.get("title"),
                "price_usd": car_data.get("price_usd"),
                "odometer": car_data.get("odometer") or 0,
                "username": car_data.get("username"),
                "phone_number": phone_numbers_str,
                "image_url": car_data.get("image_url"),
                "images_count": car_data.get("images_count"),
                "car_number": car_data.get("car_number"),
                "car_vin": car_data.get("car_vin"),
                "datetime_found": datetime.now(),
            }

            # Safe insert with locking
            car_id = safe_insert_car(db, car_insert_data)

            return car_id is not None
        except Exception as e:
            logger.error(
                f"Error saving car {car_data.get('url')}: {str(e)}",
                exc_info=True,
            )
            return False

    async def _process_car_page(
        self, car_url: str, client: httpx.AsyncClient, db: Session, attempt: int = 1
    ) -> Optional[Dict[str, Any]]:
        """
        Process car page with retry attempts on errors.

        First checks if a record with the given URL exists in the database,
        and only then makes a request to the car page.

        Args:
            car_url (str): Car page URL.
            client (httpx.AsyncClient): HTTP client for making requests.
            db (Session): SQLAlchemy database session.
            attempt (int, optional): Current attempt number. Default is 1.

        Returns:
            Optional[Dict[str, Any]]: Dictionary with car data or None on error.

        Note:
            On error, function tries to repeat the request up to self.retry_count times
            with self.retry_delay seconds delay between attempts.
        """
        # First check if a record with this URL exists in the database
        car_id = check_url_exists(db, car_url)
        if car_id:
            logger.info(f"Car with URL {car_url} already exists in DB, ID: {car_id}")
            return None

        try:
            async with self._error_handler("parsing car page", car_url):
                return await self.car_parser.parse(car_url, client=client)
        except Exception as e:
            if attempt < self.retry_count:
                logger.warning(
                    f"Attempt {attempt} failed for {car_url}. Retrying in {self.retry_delay} sec."
                )
                await asyncio.sleep(self.retry_delay)
                return await self._process_car_page(car_url, client, db, attempt + 1)
            return None

    async def run(self) -> Dict[str, int]:
        """
        Start the scraping process.

        Main method that performs the full scraping cycle:
        1. Collects car links from search pages
        2. Checks which links are already processed (exist in DB)
        3. Processes each new car page in parallel immediately after getting links
        4. Saves data to database

        Returns:
            Dict[str, int]: Scraping process statistics with keys:
                - processed (int): Number of processed cars
                - saved (int): Number of cars saved to database
                - skipped (int): Number of skipped cars (already in DB)

        Note:
            Method uses limitation on concurrent requests count
            through asyncio.Semaphore to prevent server overload.
        """
        logger.info(f"Starting AutoRia scraper. URL: {self.start_url}")
        processed_count = saved_count = skipped_count = 0
        car_links_total = []
        sem = asyncio.Semaphore(SCRAPER_CONCURRENCY)  # Concurrency limitation

        # Function to process one car
        async def process_car(car_url, client, db):
            nonlocal processed_count, saved_count
            async with sem:
                car_details = await self._process_car_page(car_url, client, db)
                processed_count += 1
                if car_details and self._save_car_data(db, car_details):
                    saved_count += 1

        try:
            async with self._error_handler("collecting links", self.start_url):
                async with httpx.AsyncClient(
                    headers={"User-Agent": self.ua.random}
                ) as client:
                    logger.info(f"Starting link collection from {self.start_url}")

                    # All car processing tasks
                    car_tasks = []

                    with get_db() as db:
                        # Counter for tracking total number of processed URLs (including skipped)
                        total_urls_count = 0
                        # Page counter
                        page_count = 0
                        current_url = self.start_url

                        # List of URLs that already exist in DB (for optimization)
                        existing_urls = set()

                        # Process each search page
                        while current_url:
                            if MAX_PAGES_TO_PARSE and page_count >= MAX_PAGES_TO_PARSE:
                                logger.info(
                                    f"Reached limit of {MAX_PAGES_TO_PARSE} pages."
                                )
                                break

                            # Parse search page
                            page_data = await self.search_parser.parse_page(
                                current_url, client
                            )
                            car_links = page_data["car_links"]
                            next_url = page_data["next_page_url"]

                            logger.info(
                                f"Found {len(car_links)} links on page {page_count}."
                            )

                            # Check for duplicates before adding to total list
                            new_links = []
                            for link in car_links:
                                if link not in car_links_total:
                                    new_links.append(link)
                                    car_links_total.append(link)

                            logger.info(
                                f"Added {len(new_links)} new unique links (filtered {len(car_links) - len(new_links)} duplicates)."
                            )

                            # Batch URL check in database
                            batch_urls_to_check = [
                                url for url in new_links if url not in existing_urls
                            ]
                            if batch_urls_to_check:
                                batch_existing = check_urls_batch(
                                    db, batch_urls_to_check
                                )
                                existing_urls.update(batch_existing.keys())
                                skipped_count += len(batch_existing)
                                logger.info(
                                    f"Found {len(batch_existing)} URLs that already exist in DB"
                                )

                            # Statistics on current state
                            logger.info(
                                f"Statistics: total URLs: {total_urls_count}, skipped: {skipped_count}, "
                                f"tasks created: {len(car_tasks)}, limit: {MAX_CARS_TO_PROCESS or 'not set'}"
                            )

                            # Start processing only new cars from current page
                            for car_url in new_links:
                                # Increase total URL counter
                                total_urls_count += 1

                                # Check limit on total number of URLs
                                if (
                                    MAX_CARS_TO_PROCESS
                                    and total_urls_count > MAX_CARS_TO_PROCESS
                                ):
                                    logger.info(
                                        f"Reached limit of {MAX_CARS_TO_PROCESS} URLs (processed + skipped)."
                                    )
                                    break

                                # Skip URLs that already exist in DB
                                if car_url in existing_urls:
                                    logger.debug(
                                        f"Skipping {car_url} - already exists in DB"
                                    )
                                    continue

                                logger.debug(
                                    f"Processing {len(car_tasks)+1}/{MAX_CARS_TO_PROCESS or 'unlimited'}: {car_url}"
                                )
                                task = asyncio.create_task(
                                    process_car(car_url, client, db)
                                )
                                car_tasks.append(task)

                            # Check if we reached the limit
                            if (
                                MAX_CARS_TO_PROCESS
                                and total_urls_count >= MAX_CARS_TO_PROCESS
                            ):
                                logger.info(
                                    f"Reached limit of {MAX_CARS_TO_PROCESS} URLs (processed + skipped)."
                                )
                                break

                            # Move to next page if it exists
                            if next_url:
                                current_url = next_url
                                page_count += 1
                                await asyncio.sleep(1)  # Pause between pages
                            else:
                                logger.info("Reached last search page.")
                                break

                        # Wait for all car processing tasks to complete
                        if car_tasks:
                            await asyncio.gather(*car_tasks)

            logger.info(
                f"Scraping completed. Pages processed: {page_count}. Total links: {len(car_links_total)}. "
                f"Skipped (already in DB): {skipped_count}. Cars processed: {processed_count}, saved: {saved_count}"
            )
            return {
                "processed": processed_count,
                "saved": saved_count,
                "skipped": skipped_count,
            }
        except Exception as e:
            logger.critical(
                f"Critical error in scraping process: {str(e)}", exc_info=True
            )
            return {
                "processed": processed_count,
                "saved": saved_count,
                "skipped": skipped_count,
            }


# For manual launch
if __name__ == "__main__":
    scraper = AutoRiaScraper()
    asyncio.run(scraper.run())
