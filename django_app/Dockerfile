# /home/Dev/AICoachAssistant/django_app/Dockerfile
# syntax=docker/dockerfile:1
FROM python:3.10-slim

# 1) Системные зависимости + netcat + ffmpeg
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      build-essential \
      libpq-dev \
      gcc \
      netcat-openbsd \
      ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 2) Python-зависимости
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# 3) Копируем весь код и даём права на entrypoint
COPY . /app/
RUN chmod +x /app/entrypoint.sh

# 4) Точка входа
ENTRYPOINT ["sh", "/app/entrypoint.sh"]
