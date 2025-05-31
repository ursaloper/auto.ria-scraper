"""
Main application settings.

This module contains all main configuration parameters for the auto.ria.com scraper.
Settings are loaded from environment variables using python-dotenv,
with default values in case of missing variables.

Attributes:
    BASE_DIR (Path): Base application directory.
    DUMPS_DIR (Path): Directory for storing database dumps.
    LOGS_DIR (Path): Directory for storing application logs.

    POSTGRES_DB (str): PostgreSQL database name.
    POSTGRES_USER (str): PostgreSQL username.
    POSTGRES_PASSWORD (str): PostgreSQL user password.
    POSTGRES_HOST (str): PostgreSQL host.
    POSTGRES_PORT (str): PostgreSQL port.
    DATABASE_URL (str): Full URL for database connection.

    REDIS_HOST (str): Redis host.
    REDIS_PORT (str): Redis port.
    REDIS_URL (str): Full URL for Redis connection.

    CELERY_BROKER_URL (str): Message broker URL for Celery.
    CELERY_RESULT_BACKEND (str): Result backend URL for Celery.

    SCRAPER_START_URL (str): Starting URL for scraping.
    SCRAPER_START_TIME (str): Daily scraping start time in "HH:MM" format.
    DUMP_TIME (str): Database dump creation time in "HH:MM" format.
    SCRAPER_CONCURRENCY (int): Number of concurrent scraper requests.
    MAX_PAGES_TO_PARSE (int): Maximum number of pages to parse (0 - no limit).
    MAX_CARS_TO_PROCESS (int): Maximum number of cars to process (0 - no limit).

    LOG_LEVEL (str): Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    LOG_FILE (str): Log file name.
    LOG_FORMAT (str): Log entry format.
    LOG_DATE_FORMAT (str): Date and time format in logs.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base paths
BASE_DIR = Path("/app")  # Fixed path in container
DUMPS_DIR = BASE_DIR / "dumps"
LOGS_DIR = BASE_DIR / "logs"

# Create directories if they don't exist
DUMPS_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# Database settings
POSTGRES_DB = os.getenv("POSTGRES_DB", "autoria")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres_password")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "db")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

# Redis settings
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"

# Celery settings
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL

# Scraper settings
SCRAPER_START_URL = os.getenv(
    "SCRAPER_START_URL",
    "https://auto.ria.com/search/?lang_id=2&page=0&countpage=100&indexName=auto&custom=1&abroad=2",
)
SCRAPER_START_TIME = os.getenv("SCRAPER_START_TIME", "12:00")
DUMP_TIME = os.getenv("DUMP_TIME", "00:00")
SCRAPER_CONCURRENCY = int(os.getenv("SCRAPER_CONCURRENCY", "3"))
MAX_PAGES_TO_PARSE = int(os.getenv("MAX_PAGES_TO_PARSE", "0"))  # 0 - no limit
MAX_CARS_TO_PROCESS = int(os.getenv("MAX_CARS_TO_PROCESS", "0"))  # 0 - no limit

# Logging settings
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "scraper.log")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
