web: gunicorn libscanner.wsgi --log-file -
worker: celery -A libscanner worker --loglevel=info --concurrency=1
release: python manage.py migrate --noinput
