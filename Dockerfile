# syntax=docker/dockerfile:1
FROM python:3.10-slim

# Системные зависимости и переменные среды
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LANG=C.UTF-8 \
    TZ=UTC \
    # Переменные для Playwright
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    DISPLAY=:99 \
    # Добавляем путь к приложению в PYTHONPATH
    PYTHONPATH=/app

# Установка необходимых пакетов для Playwright
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    wget \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libxshmfence1 \
    libxkbcommon0 \
    libxrender1 \
    libx11-xcb1 \
    xvfb \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Создаём каталоги для хранения данных и временных файлов
RUN mkdir -p /app/dumps /app/logs /tmp/.X11-unix && \
    chmod 1777 /tmp/.X11-unix

WORKDIR /app

# Копируем сначала requirements.txt для лучшего кэширования слоев
COPY requirements.txt .

# Установка Python зависимостей и Playwright
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    playwright install --with-deps chromium

# Копируем код приложения
COPY . .

# Запуск
CMD ["python", "-m", "app.main"] 