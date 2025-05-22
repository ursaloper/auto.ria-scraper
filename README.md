# auto.ria.com Scraper

[![Python 3.10](https://img.shields.io/badge/python-3.10-blue.svg)](https://www.python.org/downloads/release/python-3100/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-13+-blue.svg)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-ready-blue.svg)](https://www.docker.com/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Высокопроизводительное асинхронное приложение для сбора и анализа данных о подержанных автомобилях с платформы AutoRia.

## 📋 Описание

AutoRia Scraper — это эффективный инструмент для сбора данных об автомобилях с сайта auto.ria.com. Приложение использует асинхронный подход на базе httpx+BeautifulSoup4 для максимальной производительности и экономии ресурсов.

### Собираемые данные:
- 💰 Информация о ценах в USD
- 🔍 Характеристики автомобилей (пробег, VIN-код, госномер)
- 👤 Контактные данные продавцов (имя, телефон)
- 🖼️ Информация о фотографиях и медиа-материалах
- 📊 Дата и время обнаружения объявления скрапером

### Преимущества:
- ⚡ **Высокая производительность** — асинхронные HTTP-запросы с httpx
- 🔄 **Устойчивость** — автоматические повторные попытки при ошибках
- 📈 **Масштабируемость** — настраиваемое количество одновременных запросов
- 🧠 **Интеллектуальный сбор данных** — двухэтапный процесс сбора (основные данные + телефон)
- 📝 **Подробное логирование** — отслеживание всех этапов сбора данных
- 🗃️ **Автоматические бэкапы** — регулярное резервное копирование базы данных

## 🔧 Технологии

- **Python 3.10** — современная версия языка программирования
- **PostgreSQL** — надежная реляционная СУБД для хранения данных
- **SQLAlchemy** — мощный ORM для работы с базой данных
- **httpx** — асинхронный HTTP-клиент нового поколения
- **BeautifulSoup4** — эффективный парсер HTML-страниц
- **asyncio** — библиотека для асинхронного программирования
- **Celery** — распределенная очередь задач для автоматизации процессов
- **Docker & Docker Compose** — контейнеризация для простого развертывания

## 📂 Структура проекта

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
    │   ├── autoria.py  # Основной скрапер
    │   ├── base.py     # Базовый класс скрапера
    │   └── parsers/
    │       ├── car_page.py    # Парсер страницы автомобиля
    │       └── search_page.py # Парсер страницы поиска
    └── tasks/          # Celery задачи
        ├── __init__.py
        ├── backup.py   # Задачи резервного копирования
        └── scraping.py # Задачи сбора данных
```

## 🚀 Установка и запуск

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

3. Настройте переменные окружения в .env:
```bash
nano .env
```

4. Запустите приложение:
```bash
docker-compose up -d
```

5. Просмотр логов:
```bash
docker-compose logs -f
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

3. Настройте .env файл:
```bash
cp .env.example .env
nano .env
```

4. Запустите приложение:
```bash
python -m app.main
```

## 🤖 Управление Celery

Для ручного запуска задач и мониторинга очереди используйте:

### Задачи скрапинга и бэкапа

- **Создать дамп базы данных вручную:**
  ```bash
  docker-compose exec celery_worker celery -A app call app.tasks.backup.manual_backup
  ```
- **Запустить скрапинг вручную:**
  ```bash
  docker-compose exec celery_worker celery -A app call app.tasks.scraping.manual_scrape
  ```
- **Запустить скрапинг с определенного URL:**
  ```bash
  docker-compose exec celery_worker celery -A app call app.tasks.scraping.manual_scrape --args='["https://auto.ria.com/uk/car/mercedes-benz/"]'
  ```

### Мониторинг Celery

- **Показать зарегистрированные задачи:**
  ```bash
  docker-compose exec celery_worker celery -A app inspect registered
  ```
- **Показать задачи в очереди:**
  ```bash
  docker-compose exec celery_worker celery -A app inspect reserved
  ```
- **Показать активные задачи:**
  ```bash
  docker-compose exec celery_worker celery -A app inspect active
  ```
- **Показать историю выполненных задач:**
  ```bash
  docker-compose exec celery_worker celery -A app inspect revoked
  ```

## ⚙️ Конфигурация

Основные настройки находятся в файле `.env`:

| Параметр | Описание | Пример |
|----------|----------|--------|
| `DATABASE_URL` | URL подключения к PostgreSQL | `postgresql://user:password@postgres:5432/autoria` |
| `SCRAPING_TIME` | Время запуска сбора данных | `12:00` (каждый день в 12:00) |
| `DUMP_TIME` | Время создания дампа БД | `00:00` (каждый день в 00:00) |
| `AUTORIA_START_URL` | Начальная страница для сбора данных | `https://auto.ria.com/uk/car/used/` |
| `MAX_PAGES_TO_PARSE` | Максимальное количество страниц для парсинга | `10` |
| `MAX_CARS_TO_PROCESS` | Максимальное количество автомобилей для обработки | `100` |
| `SCRAPER_CONCURRENCY` | Максимальное количество одновременных запросов | `5` |

## 💾 Дампы базы данных

- Дампы создаются автоматически каждый день в указанное время
- Хранятся в директории `dumps/`
- Формат имени: `autoria_dump_YYYY-MM-DD_HH-MM-SS.sql`
- Автоматическое удаление старых дампов (по умолчанию хранятся 30 дней)

## 📊 Логирование

Система логирования предоставляет детальную информацию о работе приложения:

- Все логи доступны в файле `logs/scraper.log`
- Настроена ротация логов (максимальный размер файла: 10MB)
- Ведется отдельное логирование для каждого модуля
- Уровни логирования: DEBUG, INFO, WARNING, ERROR, CRITICAL