#!/bin/sh
set -e

# Ждём, пока Postgres станет доступен
echo "=== Waiting for Postgres at ${POSTGRES_HOST:-db}:${POSTGRES_PORT:-5432}…"
until nc -z ${POSTGRES_HOST:-db} ${POSTGRES_PORT:-5432}; do
  sleep 1
done
echo "=== Postgres is up, continue…"

# Миграции
echo "=== Apply Django migrations…"
python manage.py migrate --noinput

# Статика
echo "=== Collect static files…"
python manage.py collectstatic --noinput

# Запуск Django (можно заменить на gunicorn)
echo "=== Start Django runserver…"
python manage.py runserver 0.0.0.0:8000 &

# Запуск Telegram-бота
echo "=== Start Telegram bot…"
exec python telegram_bot.py
