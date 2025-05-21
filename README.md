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
├── .dockerignore
├── .env                # Переменные окружения (создайте вручную)
├── .env.example        # Пример .env файла
├── .gitignore
├── Dockerfile          # Docker-образ приложения
├── README.md           # Документация
├── docker-compose.yml  # Docker Compose конфигурация
├── requirements.txt    # Python зависимости
├── tests/              # Тесты
├── logs/               # Логи приложения
│   └── scraper.log
├── dumps/              # Дампы базы данных
│   └── autoria_dump_YYYY-MM-DD_HH-MM-SS.sql
└── app/                # Основной код приложения
    ├── __init__.py
    ├── main.py         # Точка входа
    ├── core/           # База данных и модели
    │   ├── __init__.py
    │   ├── database.py
    │   └── models.py
    ├── config/         # Конфигурация
    │   ├── __init__.py
    │   ├── celery_config.py
    │   └── settings.py
    ├── utils/          # Утилиты
    │   ├── __init__.py
    │   ├── db_dumper.py
    │   └── logger.py
    ├── scraper/        # Логика парсинга
    │   ├── __init__.py
    │   ├── autoria.py
    │   ├── base.py
    │   ├── parsers/
    │   │   ├── car_page.py
    │   │   └── search_page.py
    │   └── browser/
    │       ├── manager.py
    │       └── utils.py
    └── tasks/          # Celery задачи
        ├── __init__.py
        ├── backup.py
        └── scraping.py
```

## Технологии
- Python 3.10
- PostgreSQL
- SQLAlchemy
- BeautifulSoup4
- Playwright
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
```bash
nano .env
```

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

## Manual Celery commands
Для ручного запуска задач и мониторинга очереди используйте:

- **Создать дамп базы данных вручную:**
  ```bash
  sudo docker-compose exec celery_worker celery -A app call app.tasks.backup.manual_backup
  ```
- **Запустить скрапинг вручную:**
  ```bash
  sudo docker-compose exec celery_worker celery -A app call app.tasks.scraping.manual_scrape
  ```
- **Показать зарегистрированные задачи Celery:**
  ```bash
  sudo docker-compose exec celery_worker celery -A app inspect registered
  ```
- **Показать задачи в очереди (reserved):**
  ```bash
  sudo docker-compose exec celery_worker celery -A app inspect reserved
  ```
- **Показать активные задачи (active):**
  ```bash
  sudo docker-compose exec celery_worker celery -A app inspect active
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
- Формат имени: autoria_dump_YYYY-MM-DD_HH-MM-SS.sql 