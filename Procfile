web: gunicorn libscanner.wsgi --log-file - --bind 0.0.0.0:$PORT
worker: celery -A libscanner worker --loglevel=info --concurrency=1 --without-gossip --without-mingle --without-heartbeat --max-tasks-per-child=1000
release: python manage.py migrate --noinput
