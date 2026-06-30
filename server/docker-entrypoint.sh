#!/bin/bash
set -e

APP_USER=appuser

run_as_app() {
    runuser -u "$APP_USER" -- "$@"
}

mkdir -p /app/staticfiles
chown -R "$APP_USER:$APP_USER" /app/staticfiles

echo "→ Running database migrations..."
run_as_app python manage.py migrate --noinput

echo "→ Collecting static files..."
run_as_app python manage.py collectstatic --noinput --clear

# Create superuser if DJANGO_SUPERUSER_EMAIL and DJANGO_SUPERUSER_PASSWORD are set
if [ -n "$DJANGO_SUPERUSER_EMAIL" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
    echo "→ Creating/updating superuser ($DJANGO_SUPERUSER_EMAIL)..."
    run_as_app python manage.py shell -c "
from django.contrib.auth import get_user_model;
User = get_user_model();
if not User.objects.filter(email='$DJANGO_SUPERUSER_EMAIL').exists():
    User.objects.create_superuser(email='$DJANGO_SUPERUSER_EMAIL', password='$DJANGO_SUPERUSER_PASSWORD')
    print('Superuser created.')
else:
    print('Superuser already exists.')
"
fi

# If the command is "celery", run celery worker instead of gunicorn
if [ "$1" = "celery" ]; then
    echo "→ Starting celery worker..."
    # Pass through any additional celery arguments from docker compose command
    shift
    exec runuser -u "$APP_USER" -- celery -A _Project "$@"
fi

echo "→ Starting gunicorn..."
exec runuser -u "$APP_USER" -- gunicorn '_Project.wsgi' --bind=0.0.0.0:8000 --workers=4 --timeout=120 --home=/tmp
