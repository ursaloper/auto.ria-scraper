# AutoRia Scraper

Приложение для автоматического сбора данных о подержанных автомобилях с платформы AutoRia.

## Описание
Приложение выполняет ежедневный сбор данных об автомобилях с сайта AutoRia, включая:
- Информацию о ценах
- Характеристики автомобилей
- Контактные данные продавцов
- Фотографии и другие медиа-материалы

## Структура проекта
```
AutoRiaScraper/
├── app/                  # Основной код приложения
├── dumps/                # Директория для дампов базы данных
├── logs/                 # Логи приложения
├── tests/                # Тесты
├── .env                  # Настройки окружения
├── docker-compose.yml    # Конфигурация Docker
├── Dockerfile           # Сборка Docker образа
└── requirements.txt     # Зависимости Python
```

## Технологии
- Python 3.10
- PostgreSQL
- SQLAlchemy
- BeautifulSoup4
- Selenium WebDriver
- Celery
- Docker & Docker Compose

## Установка и запуск

### Через Docker (рекомендуется)
1. Склонируйте репозиторий:
```bash
git clone https://github.com/ursaloper/auto.ria-scraper
cd auto.ria-scraper
```

2. Создайте файл .env на основе .env.example:
```bash
cp .env.example .env
```

3. Настройте переменные окружения в .env

4. Запустите приложение:
```bash
docker-compose up -d
```

### Локальная установка
1. Создайте виртуальное окружение:
```bash
python -m venv venv
source venv/bin/activate  # Linux/MacOS
# или
venv\Scripts\activate     # Windows
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Настройте .env файл

4. Запустите приложение:
```bash
python -m app/main.py
```

## Конфигурация
Основные настройки находятся в файле .env:
- DATABASE_URL - URL подключения к PostgreSQL
- SCRAPING_TIME - Время запуска сбора данных (например, "12:00")
- DUMP_TIME - Время создания дампа БД (например, "00:00")
- AUTORIA_START_URL - Начальная страница для сбора данных

## Дампы базы данных
- Дампы создаются автоматически каждый день в указанное время
- Хранятся в директории dumps/
- Формат имени: autoria_dump_YYYY-MM-DD.sql 