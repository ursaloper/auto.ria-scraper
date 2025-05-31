# syntax=docker/dockerfile:1
FROM python:3.10-slim

# System dependencies and environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LANG=C.UTF-8 \
    TZ=UTC \
    PYTHONPATH=/app

# Install necessary packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ca-certificates \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Create directories for data storage and temporary files
RUN mkdir -p /app/dumps /app/logs

WORKDIR /app

# Copy requirements.txt first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Run
CMD ["python", "-m", "app.main"] 