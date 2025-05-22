# syntax=docker/dockerfile:1
FROM python:3.10-slim

# Системные зависимости и переменные среды
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LANG=C.UTF-8 \
    TZ=UTC \
    PYTHONPATH=/app

# Установка необходимых пакетов
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ca-certificates \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Создаём каталоги для хранения данных и временных файлов
RUN mkdir -p /app/dumps /app/logs

WORKDIR /app

# Копируем сначала requirements.txt для лучшего кэширования слоев
COPY requirements.txt .

# Установка Python зависимостей
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копируем код приложения
COPY . .

# Запуск
CMD ["python", "-m", "app.main"] 