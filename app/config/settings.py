"""
Основные настройки приложения.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Базовые пути
BASE_DIR = Path("/app")  # Фиксированный путь в контейнере
DUMPS_DIR = BASE_DIR / "dumps"
LOGS_DIR = BASE_DIR / "logs"

# Создание директорий если они не существуют
DUMPS_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# Настройки базы данных
POSTGRES_DB = os.getenv("POSTGRES_DB", "autoria")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres_password")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "db")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

# Настройки Redis
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"

# Настройки Celery
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL

# Настройки скрапера
SCRAPER_START_URL = os.getenv("SCRAPER_START_URL", "https://auto.ria.com/uk/car/used/")
SCRAPER_START_TIME = os.getenv("SCRAPER_START_TIME", "12:00")
DUMP_TIME = os.getenv("DUMP_TIME", "00:00")
SCRAPER_CONCURRENCY = int(os.getenv("SCRAPER_CONCURRENCY", "3"))
MAX_PAGES_TO_PARSE = int(os.getenv("MAX_PAGES_TO_PARSE", "0"))  # 0 - без ограничений
MAX_CARS_TO_PROCESS = int(os.getenv("MAX_CARS_TO_PROCESS", "0"))  # 0 - без ограничений

# Настройки логирования
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "scraper.log")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
