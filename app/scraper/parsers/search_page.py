"""
Auto.ria.com search page parser (asynchronous, httpx+bs4).

This module implements an asynchronous parser for extracting car links list
from auto.ria.com search pages. Uses httpx for HTTP requests and BeautifulSoup for
HTML parsing. Supports pagination and limiting the number of processed pages.

Attributes:
    logger: Logger for registering parsing events.
    SCRAPER_START_URL: Starting page URL for scraping (from settings).

Classes:
    SearchPageParser: Parser for auto.ria.com search pages.
"""

import asyncio
import random
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import httpx  # type: ignore
from bs4 import BeautifulSoup

from app.config.settings import SCRAPER_START_URL
from app.scraper.base import BaseScraper
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SearchPageParser(BaseScraper):
    """
    Asynchronous parser for extracting data from AutoRia search page.

    Extracts links to car pages from search result pages.
    Supports pagination for processing multi-page search results.

    Attributes:
        current_page (int): Current search page number (starting from 0).
        base_url (str): AutoRia website base URL.
    """

    def __init__(self):
        """
        Initialize search page parser.

        Sets initial values for page counter and base URL.
        """
        self.current_page = 0  # Start with page=0
        self.base_url = "https://auto.ria.com"

    def _extract_car_links(self, soup: BeautifulSoup) -> List[str]:
        """
        Extract links to car pages.

        Finds and extracts links to pages with detailed car information
        from search page HTML code.

        Args:
            soup (BeautifulSoup): BeautifulSoup object with search page HTML code.

        Returns:
            List[str]: List of car page URLs.
        """
        car_links = []
        ticket_items = soup.select("section.ticket-item")
        for item in ticket_items:
            link_tag = item.select_one("a.m-link-ticket")
            if link_tag and link_tag.has_attr("href"):
                car_links.append(link_tag["href"])

        page_str = (
            f"on page {self.current_page}"
            if self.current_page > 0
            else "on first page"
        )
        logger.info(f"Found {len(car_links)} car links {page_str}")
        return car_links

    def _get_next_page_url(self, current_url: str) -> str:
        """
        Generate next page URL by incrementing page parameter.

        Analyzes current URL, increments page number in page parameter
        and forms new URL for next search results page.

        Args:
            current_url (str): Current search page URL.

        Returns:
            str: Next search page URL.

        Note:
            Simply increments page number by 1, regardless of total page count.
        """
        # Parse current URL
        parsed_url = urlparse(current_url)
        query_params = parse_qs(parsed_url.query)

        # Determine current page number from URL
        current_page_num = 0
        if "page" in query_params and query_params["page"]:
            try:
                current_page_num = int(query_params["page"][0])
            except (ValueError, IndexError):
                current_page_num = 0

        # Increment page number by 1
        next_page = current_page_num + 1
        query_params["page"] = [str(next_page)]

        # Build new URL
        new_query = urlencode(query_params, doseq=True)
        next_url_parts = list(parsed_url)
        next_url_parts[4] = new_query
        next_url = urlunparse(next_url_parts)
        logger.info(f"Generated URL for page {next_page}: {next_url}")
        return next_url

    async def parse_page(self, url: str, client: httpx.AsyncClient) -> Dict[str, Any]:
        """
        Parse single search page.

        Makes HTTP request to specified URL, extracts car links
        and forms URL for next search page.

        Args:
            url (str): Search page URL for parsing.
            client (httpx.AsyncClient): HTTP client for making requests.

        Returns:
            Dict[str, Any]: Dictionary with parsing results containing:
                - car_links (List[str]): List of car page links.
                - next_page_url (Optional[str]): Next page URL or None
                  if no links found (end of list).

        Raises:
            Exception: Catches and logs all exceptions during HTML request.
        """
        # Update current page based on URL
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        if "page" in query_params and query_params["page"]:
            try:
                self.current_page = int(query_params["page"][0])
            except (ValueError, IndexError):
                self.current_page = 0

        logger.info(f"Parsing search page: {url} (page {self.current_page})")
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                resp = await client.get(url)
                resp.raise_for_status()
                html = resp.text
                break
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 503 and retry_count < max_retries - 1:
                    retry_count += 1
                    wait_time = (
                        5 + random.randint(1, 5) * retry_count
                    )  # Increase wait time with each attempt
                    logger.warning(
                        f"Received 503 status for {url}. Retry {retry_count}/{max_retries} in {wait_time} sec."
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Failed to get HTML for URL: {url}: {e}")
                    return {"car_links": [], "next_page_url": None}
            except Exception as e:
                logger.error(f"Failed to get HTML for URL: {url}: {e}")
                return {"car_links": [], "next_page_url": None}
        else:
            # If all attempts exhausted
            logger.error(f"All attempts exhausted for getting HTML for URL: {url}")
            return {"car_links": [], "next_page_url": None}

        soup = self.get_soup(html)
        car_links = self._extract_car_links(soup)

        # If no ads on page, consider we reached the end
        if not car_links:
            logger.info(
                f"No ads found on page {self.current_page}. Reached end of list."
            )
            return {"car_links": [], "next_page_url": None}

        # Always generate next page URL
        next_page_url = self._get_next_page_url(url)
        return {"car_links": car_links, "next_page_url": next_page_url}

    async def parse(
        self,
        start_url: str = SCRAPER_START_URL,
        max_pages: Optional[int] = None,
        max_cars: Optional[int] = None,
        client: Optional[httpx.AsyncClient] = None,
    ) -> List[str]:
        """
        Main method for parsing AutoRia search pages.

        Performs sequential parsing of search pages starting from specified URL,
        and collects car page links. Supports limiting by
        page count and total number of collected links.

        Args:
            start_url (str, optional): Starting search page URL.
                By default uses URL from application settings.
            max_pages (Optional[int], optional): Maximum number of pages to parse.
                None means no limit.
            max_cars (Optional[int], optional): Maximum number of car links.
                None means no limit.
            client (Optional[httpx.AsyncClient], optional): HTTP client for making requests.
                If not specified, creates new client that closes after use.

        Returns:
            List[str]: List of car page URLs.

        Note:
            Method makes 1 second pause between search page requests.
        """
        all_car_links = []
        current_url: Optional[str] = start_url
        pages_processed = 0  # Processed pages counter
        close_client = False
        if client is None:
            client = httpx.AsyncClient()
            close_client = True
        try:
            while current_url:
                # Check page limit
                if max_pages and pages_processed >= max_pages:
                    logger.info(f"Reached limit of {max_pages} pages.")
                    break

                page_data = await self.parse_page(current_url, client)
                all_car_links.extend(page_data["car_links"])
                next_url = page_data["next_page_url"]

                # Increment processed pages counter
                pages_processed += 1

                if next_url:
                    logger.info(f"Moving to next page: {next_url}")
                    current_url = next_url
                    await asyncio.sleep(1)  # Pause between pages
                else:
                    logger.info("Reached last search page.")
                    break
        finally:
            if close_client:
                await client.aclose()

        # Limit total number of links if max_cars is set
        if max_cars:
            all_car_links = all_car_links[:max_cars]
            logger.info(
                f"Limited to {len(all_car_links)} car links by max_cars={max_cars}"
            )

        logger.info(f"Total found {len(all_car_links)} car links.")
        return all_car_links


# Usage example (for testing)
if __name__ == "__main__":
    parser = SearchPageParser()
    links = parser.parse(max_pages=2)  # Parse no more than 2 pages for test

    if links:
        logger.info(f"First 5 found links:")
        for link in links[:5]:
            logger.info(link)
    else:
        logger.info("No links found.")
