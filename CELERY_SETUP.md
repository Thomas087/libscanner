# Celery Task Queue Setup for Libscanner

This document explains how to use the new Celery-based task queue system for running the `scrape_animal_keywords` process without timeouts.

## Overview

The scraping process has been enhanced with Celery task queue support to prevent timeouts during long-running scraping operations. This allows the scraping to run in the background without blocking the web server.

## Dependencies

The following packages have been added to `requirements.txt`:

- `celery==5.3.4` - Task queue framework
- `redis==5.0.1` - Message broker for Celery

## Configuration

### Environment Variables

Set the following environment variables:

```bash
# Redis URL for Celery broker and result backend
REDIS_URL=redis://localhost:6379/0

# For production (Heroku), this will be automatically set by Redis addon
# For development, you can use a local Redis instance
```

### Local Development

1. **Install Redis** (if not already installed):

   ```bash
   # macOS with Homebrew
   brew install redis
   brew services start redis

   # Ubuntu/Debian
   sudo apt-get install redis-server
   sudo systemctl start redis
   ```

2. **Install Python dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

3. **Start Celery worker** (in a separate terminal):

   ```bash
   celery -A libscanner worker --loglevel=info --concurrency=1
   ```

4. **Run the scraping command with async flag**:
   ```bash
   python manage.py scrape_animal_keywords --async
   ```

## Usage

### Asynchronous Scraping

To run scraping asynchronously (recommended for long operations):

```bash
python manage.py scrape_animal_keywords --async
```

This will:

- Start a background task
- Return a task ID immediately
- Continue processing in the background
- Not timeout even for long scraping operations

### Check Task Status

To check the status of a running task:

```bash
python manage.py scrape_animal_keywords --task-id <TASK_ID>
```

### Synchronous Scraping (Original Behavior)

To run scraping synchronously (for testing or short operations):

```bash
python manage.py scrape_animal_keywords
```

## Command Options

All existing options work with both async and sync modes:

```bash
# Filter by region
python manage.py scrape_animal_keywords --async --region "Bretagne"

# Filter by prefecture
python manage.py scrape_animal_keywords --async --prefecture "Morbihan"

# Custom keywords
python manage.py scrape_animal_keywords --async --keywords "bovin" "porcin"

# Output to file
python manage.py scrape_animal_keywords --async --output results.json --format json

# Check task status
python manage.py scrape_animal_keywords --task-id abc123-def456-ghi789
```

## Production Deployment (Heroku)

### 1. Add Redis Addon

```bash
heroku addons:create heroku-redis:mini
```

This automatically sets the `REDIS_URL` environment variable.

### 2. Scale Worker Dyno

```bash
# Scale up the worker dyno
heroku ps:scale worker=1

# Check dyno status
heroku ps
```

### 3. Deploy

```bash
git add .
git commit -m "Add Celery task queue support"
git push heroku main
```

## Monitoring

### Check Worker Status

```bash
# View worker logs
heroku logs --tail --dyno worker

# Check all dynos
heroku ps
```

### Task Monitoring

The task provides progress updates during execution:

- Current operation count
- Current prefecture being scraped
- Current keyword being processed
- Overall progress percentage

## Benefits

1. **No Timeouts**: Long-running scraping operations won't timeout
2. **Background Processing**: Web server remains responsive
3. **Progress Tracking**: Real-time progress updates
4. **Scalability**: Can scale workers independently
5. **Reliability**: Tasks can be retried on failure
6. **Monitoring**: Easy to monitor task status and progress

## Troubleshooting

### Common Issues

1. **Redis Connection Error**:

   - Ensure Redis is running: `redis-cli ping`
   - Check `REDIS_URL` environment variable

2. **Worker Not Processing Tasks**:

   - Ensure worker dyno is running: `heroku ps`
   - Check worker logs: `heroku logs --tail --dyno worker`

3. **Task Stuck in PENDING**:
   - Check if worker is running
   - Verify Redis connection
   - Check task logs for errors

### Development Tips

- Use `--async` for any scraping operation that might take more than a few minutes
- Use `--task-id` to monitor long-running tasks
- Check logs regularly for any errors or issues
- Test locally before deploying to production

## Example Workflow

1. **Start scraping**:

   ```bash
   python manage.py scrape_animal_keywords --async --region "Bretagne"
   # Returns: Task started with ID: abc123-def456-ghi789
   ```

2. **Monitor progress**:

   ```bash
   python manage.py scrape_animal_keywords --task-id abc123-def456-ghi789
   # Shows: Task is in progress: 15/45 operations completed
   ```

3. **Check completion**:
   ```bash
   python manage.py scrape_animal_keywords --task-id abc123-def456-ghi789
   # Shows: Task completed successfully! Found 150 items.
   ```
