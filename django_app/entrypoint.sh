#!/bin/sh
set -e

echo "=== Waiting for Postgres at ${POSTGRES_HOST:-db}:${POSTGRES_PORT:-5432}…"
until nc -z ${POSTGRES_HOST:-db} ${POSTGRES_PORT:-5432}; do
  sleep 1
done

echo "=== Applying Django migrations…"
python manage.py migrate --noinput

echo "=== Ensuring superuser exists…"
python manage.py shell <<EOF
import os
from django.contrib.auth import get_user_model

User = get_user_model()
username = os.getenv('DJANGO_SUPERUSER_USERNAME')
email    = os.getenv('DJANGO_SUPERUSER_EMAIL')
password = os.getenv('DJANGO_SUPERUSER_PASSWORD')

if username and password:
    user, created = User.objects.get_or_create(
        username=username, defaults={'email': email or ''}
    )
    user.set_password(password)
    user.save()
    print(f"Superuser {'created' if created else 'updated'}: {username}")
else:
    print("Skipping superuser setup (username/password not set)")
EOF

echo "=== Collecting static files…"
python manage.py collectstatic --noinput

echo "=== Starting Gunicorn in background…"
gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --log-level info &

echo "=== Starting Telegram bot in foreground…"
exec python telegram_bot.py