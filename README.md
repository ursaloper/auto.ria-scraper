# auto.ria.com Scraper

[![Python 3.10](https://img.shields.io/badge/python-3.10-blue.svg)](https://www.python.org/downloads/release/python-3100/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-13+-blue.svg)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-ready-blue.svg)](https://www.docker.com/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

> 📖 **[Русская версия документации](README_RU.md)**

High-performance asynchronous application for collecting used car data from the auto.ria.com platform.

## 📋 Description

AutoRia Scraper is an efficient tool for collecting car data from the auto.ria.com website. The application uses an asynchronous approach based on httpx+BeautifulSoup4 for maximum performance and resource efficiency.

### Collected data:
- 💰 Price information in USD
- 🔍 Car characteristics (mileage, VIN code, license plate)
- 👤 Seller contact information (name, phone)
- 🖼️ Photo and media information
- 📊 Date and time when the listing was discovered by the scraper

### Advantages:
- ⚡ **High performance** — asynchronous HTTP requests with httpx
- 🔄 **Resilience** — automatic retry attempts on errors
- 📈 **Scalability** — configurable number of concurrent requests
- 🧠 **Intelligent data collection** — two-stage collection process (main data + phone)
- 📝 **Detailed logging** — tracking all stages of data collection
- 🗃️ **Automatic backups** — regular database backup

## 🔧 Technologies

- **Python 3.10** — modern programming language version
- **PostgreSQL** — reliable relational database for data storage
- **SQLAlchemy** — powerful ORM for database operations
- **httpx** — next-generation asynchronous HTTP client
- **BeautifulSoup4** — efficient HTML page parser
- **asyncio** — library for asynchronous programming
- **Celery** — distributed task queue for process automation
- **Docker & Docker Compose** — containerization for easy deployment

## 📂 Project Structure

```
├── .dockerignore
├── .env                # Environment variables (create manually)
├── .env.example        # Example .env file
├── .gitignore
├── Dockerfile          # Application Docker image
├── README.md           # Documentation
├── README_RU.md        # Russian documentation
├── docker-compose.yml  # Docker Compose configuration
├── requirements.txt    # Python dependencies
├── tests/              # Tests
├── logs/               # Application logs
│   └── scraper.log
├── dumps/              # Database dumps
│   └── autoria_dump_YYYY-MM-DD_HH-MM-SS.sql
└── app/                # Main application code
    ├── __init__.py
    ├── main.py         # Entry point
    ├── core/           # Database and models
    │   ├── __init__.py
    │   ├── database.py
    │   └── models.py
    ├── config/         # Configuration
    │   ├── __init__.py
    │   ├── celery_config.py
    │   └── settings.py
    ├── utils/          # Utilities
    │   ├── __init__.py
    │   ├── db_dumper.py
    │   ├── db_utils.py
    │   └── logger.py
    ├── scraper/        # Parsing logic
    │   ├── __init__.py
    │   ├── autoria.py  # Main scraper
    │   ├── base.py     # Base scraper class
    │   └── parsers/
    │       ├── car_page.py    # Car page parser
    │       └── search_page.py # Search page parser
    └── tasks/          # Celery tasks
        ├── __init__.py
        ├── backup.py   # Backup tasks
        └── scraping.py # Data collection tasks
```

## 🚀 Installation and Launch

### Via Docker (recommended)

1. Clone the repository:
```bash
git clone https://github.com/ursaloper/auto.ria-scraper
cd auto.ria-scraper
```

2. Create .env file based on .env.example:
```bash
cp .env.example .env
```

3. Configure environment variables in .env:
```bash
nano .env
```

4. Launch the application:
```bash
docker-compose up -d
```

5. View logs:
```bash
docker-compose logs -f
```

### Local Installation

1. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/MacOS
# or
venv\Scripts\activate     # Windows
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure .env file:
```bash
cp .env.example .env
nano .env
```

4. Launch the application:
```bash
python -m app.main
```

## 🤖 Celery Management

For manual task execution and queue monitoring use:

### Scraping and Backup Tasks

- **Create database dump manually:**
  ```bash
  docker-compose exec celery_worker celery -A app call app.tasks.backup.manual_backup
  ```
- **Run scraping manually:**
  ```bash
  docker-compose exec celery_worker celery -A app call app.tasks.scraping.manual_scrape
  ```
- **Run scraping from specific URL:**
  ```bash
  docker-compose exec celery_worker celery -A app call app.tasks.scraping.manual_scrape --args='["https://auto.ria.com/uk/car/mercedes-benz/"]'
  ```

### Celery Monitoring

- **Show registered tasks:**
  ```bash
  docker-compose exec celery_worker celery -A app inspect registered
  ```
- **Show queued tasks:**
  ```bash
  docker-compose exec celery_worker celery -A app inspect reserved
  ```
- **Show active tasks:**
  ```bash
  docker-compose exec celery_worker celery -A app inspect active
  ```
- **Show completed tasks history:**
  ```bash
  docker-compose exec celery_worker celery -A app inspect revoked
  ```

## ⚙️ Configuration

Main settings are located in the `.env` file:

| Parameter | Description | Example |
|-----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection URL | `postgresql://user:password@postgres:5432/autoria` |
| `SCRAPER_START_TIME` | Data collection start time | `12:00` (daily at 12:00) |
| `DUMP_TIME` | Database dump creation time | `00:00` (daily at 00:00) |
| `SCRAPER_START_URL` | Starting page for data collection | `https://auto.ria.com/uk/car/used/` |
| `MAX_PAGES_TO_PARSE` | Maximum number of pages to parse | `10` |
| `MAX_CARS_TO_PROCESS` | Maximum number of cars to process | `100` |
| `SCRAPER_CONCURRENCY` | Maximum number of concurrent requests | `5` |

## 🚄 Performance

Parser speed depends on the `SCRAPER_CONCURRENCY` parameter, which determines the number of concurrent requests. In practice, due to auto.ria.com site limitations and server-side delays, actual speed may differ from theoretical.

**Test Results:**
- Processed: 500 cars
- Added to DB: 495-496 new records
- Execution time: ~6-7 minutes (360-380 seconds)
- Efficiency: 99% (percentage of successfully processed listings)

> **Important:**
> - Increasing `SCRAPER_CONCURRENCY` above 5-7 practically doesn't speed up data collection due to site limitations and delays on auto.ria.com side.
> - Too high values may lead to temporary IP address blocking.
> - Recommended to use values 5-7 for stable and safe operation.

## 💾 Database Dumps

- Dumps are created automatically daily at specified time
- Stored in `dumps/` directory
- Filename format: `autoria_dump_YYYY-MM-DD_HH-MM-SS.sql`
- Automatic deletion of old dumps (stored for 30 days by default)

## 📊 Logging

The logging system provides detailed information about application operation:

- All logs are available in `logs/scraper.log` file
- Log rotation is configured (maximum file size: 10MB)
- Separate logging for each module
- Logging levels: DEBUG, INFO, WARNING, ERROR, CRITICAL

## 🛠️ Development

### Code Style

The project uses [Black](https://github.com/psf/black) for code formatting:

```bash
# Format code
black app/

# Check formatting
black --check app/
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📞 Support

If you have questions or need help:

- Create an [Issue](https://github.com/ursaloper/auto.ria-scraper/issues)
- Check the [Russian documentation](README_RU.md)

## ⭐ Star History

If this project helped you, please give it a star! ⭐