web: gunicorn libscanner.wsgi --log-file - --bind 0.0.0.0:$PORT
worker: celery -A libscanner worker --loglevel=info --concurrency=1 --without-gossip --without-mingle --without-heartbeat --max-tasks-per-child=1 --worker_max_tasks_per_child=1 --max-memory-per-child=200000
beat: celery -A libscanner beat --loglevel=info
release: python manage.py migrate --noinput
