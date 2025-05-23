"""
Основные настройки приложения.

Этот модуль содержит все основные параметры конфигурации для скрапера auto.ria.com.
Настройки загружаются из переменных окружения с использованием python-dotenv,
с определенными значениями по умолчанию в случае отсутствия переменных.

Attributes:
    BASE_DIR (Path): Базовая директория приложения.
    DUMPS_DIR (Path): Директория для хранения дампов базы данных.
    LOGS_DIR (Path): Директория для хранения логов приложения.

    POSTGRES_DB (str): Имя базы данных PostgreSQL.
    POSTGRES_USER (str): Имя пользователя PostgreSQL.
    POSTGRES_PASSWORD (str): Пароль пользователя PostgreSQL.
    POSTGRES_HOST (str): Хост PostgreSQL.
    POSTGRES_PORT (str): Порт PostgreSQL.
    DATABASE_URL (str): Полный URL для подключения к базе данных.

    REDIS_HOST (str): Хост Redis.
    REDIS_PORT (str): Порт Redis.
    REDIS_URL (str): Полный URL для подключения к Redis.

    CELERY_BROKER_URL (str): URL брокера сообщений для Celery.
    CELERY_RESULT_BACKEND (str): URL бэкенда результатов для Celery.

    SCRAPER_START_URL (str): Начальный URL для скрапинга.
    SCRAPER_START_TIME (str): Время начала ежедневного скрапинга в формате "ЧЧ:ММ".
    DUMP_TIME (str): Время создания дампа базы данных в формате "ЧЧ:ММ".
    SCRAPER_CONCURRENCY (int): Количество одновременных запросов скрапера.
    MAX_PAGES_TO_PARSE (int): Максимальное количество страниц для парсинга (0 - без ограничений).
    MAX_CARS_TO_PROCESS (int): Максимальное количество автомобилей для обработки (0 - без ограничений).

    LOG_LEVEL (str): Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    LOG_FILE (str): Имя файла для хранения логов.
    LOG_FORMAT (str): Формат записей в логе.
    LOG_DATE_FORMAT (str): Формат даты и времени в логах.
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
SCRAPER_START_URL = os.getenv(
    "SCRAPER_START_URL",
    "https://auto.ria.com/search/?lang_id=2&page=0&countpage=100&indexName=auto&custom=1&abroad=2",
)
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
