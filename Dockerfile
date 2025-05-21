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

# Создание непривилегированного пользователя
RUN groupadd -r pwuser && useradd -r -g pwuser -G audio,video pwuser \
    && mkdir -p /home/pwuser/Downloads \
    && chown -R pwuser:pwuser /home/pwuser

# Установка необходимых пакетов для Playwright
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    wget \
    gnupg \
    curl \
    git \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxcb1 \
    libxkbcommon0 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    fonts-liberation \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Создаём каталоги для хранения данных и временных файлов
RUN mkdir -p /app/dumps /app/logs /tmp/.X11-unix && \
    chown -R pwuser:pwuser /app /tmp/.X11-unix && \
    chmod 1777 /tmp/.X11-unix

WORKDIR /app

# Копируем сначала requirements.txt для лучшего кэширования слоев
COPY requirements.txt .

# Установка Python зависимостей и Playwright
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    playwright install --with-deps chromium && \
    chown -R pwuser:pwuser /ms-playwright

# Копируем код приложения
COPY . .
RUN chown -R pwuser:pwuser /app && \
    chmod -R 755 /app/logs

# Переключение на непривилегированного пользователя
USER pwuser

# Запуск через entrypoint скрипт
CMD ["python", "-m", "app.main"] 