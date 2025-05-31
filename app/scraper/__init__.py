"""
The scraper package contains data collection components.

This package implements asynchronous data scraping functionality from the auto.ria.com website.
Includes base classes and specialized parsers for different types of pages.
Implementation uses a combination of httpx for HTTP requests and BeautifulSoup for HTML parsing.

Modules:
    base: Abstract base class for all parsers.
    autoria: Main scraper class for the auto.ria.com website.

Subpackages:
    parsers: Specialized parsers for different types of pages:
        - search_page: Search page parser (ad listings).
        - car_page: Parser for detailed car information page.
"""
