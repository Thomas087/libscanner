# Task Management Guide for Libscanner

This guide explains how to stop, monitor, and manage Redis/Celery tasks while they're running.

## Quick Reference

### Stop a Running Task

**Method 1: Using Django Management Command**

```bash
# List all active tasks
python manage.py manage_tasks --action list

# Revoke a specific task
python manage.py manage_tasks --action revoke --task-id <TASK_ID>

# Purge all tasks from queue
python manage.py manage_tasks --action purge
```

**Method 2: Using the Task Manager Script**

```bash
# List active tasks
python task_manager.py list

# Revoke a specific task
python task_manager.py revoke --task-id <TASK_ID>

# Revoke all active tasks
python task_manager.py revoke-all

# Purge all tasks from queue
python task_manager.py purge

# Check task status
python task_manager.py status --task-id <TASK_ID>

# Show worker statistics
python task_manager.py stats

# Force stop all workers (nuclear option)
python task_manager.py force-stop
```

**Method 3: Using Python Code**

```python
from celery import current_app

# Revoke a specific task
current_app.control.revoke('task-id-here', terminate=True)

# Revoke all tasks
current_app.control.purge()
```

**Method 4: Using Redis CLI**

```bash
# Connect to Redis
redis-cli

# List all keys
KEYS *

# Remove specific task
DEL celery-task-meta-<task-id>

# Flush all Celery data (nuclear option)
FLUSHDB
```

## Detailed Usage

### 1. Monitoring Tasks

**Check what tasks are currently running:**

```bash
python manage.py manage_tasks --action list
```

**Get detailed worker statistics:**

```bash
python task_manager.py stats
```

### 2. Stopping Tasks

**Stop a specific task by ID:**

```bash
# First, get the task ID from the list command
python manage.py manage_tasks --action list

# Then revoke it
python manage.py manage_tasks --action revoke --task-id <TASK_ID>
```

**Stop all running tasks:**

```bash
python task_manager.py revoke-all
```

**Clear the entire queue:**

```bash
python manage.py manage_tasks --action purge
```

### 3. Task Status Monitoring

**Check the status of a specific task:**

```bash
python task_manager.py status --task-id <TASK_ID>
```

**Check task progress (if you have the task ID from when you started it):**

```python
from scraper.tasks import scrape_animal_keywords_task

# Get the task result
result = scrape_animal_keywords_task.AsyncResult('<TASK_ID>')
print(f"Status: {result.status}")
print(f"Progress: {result.info}")
```

## Enhanced Task Cancellation

The `scrape_animal_keywords_task` has been enhanced to handle graceful cancellation. When a task is revoked:

1. The task checks `self.is_aborted()` at each iteration
2. If revoked, it returns partial results instead of crashing
3. The task status becomes 'REVOKED' with a clear message
4. Any completed work is preserved in the results

## Production Considerations

### For Heroku Deployment

If you're running this on Heroku, you can also:

1. **Scale down workers:**

   ```bash
   heroku ps:scale worker=0
   ```

2. **Restart workers:**

   ```bash
   heroku ps:restart worker
   ```

3. **View logs:**
   ```bash
   heroku logs --tail --dyno=worker
   ```

### For Local Development

1. **Stop the Celery worker process:**

   - Find the process: `ps aux | grep celery`
   - Kill it: `kill <PID>`

2. **Restart the worker:**
   ```bash
   python start_celery_worker.py
   # or
   celery -A libscanner worker --loglevel=info --concurrency=1
   ```

## Emergency Stop

If you need to immediately stop all tasks:

1. **Kill the worker process:**

   ```bash
   pkill -f celery
   ```

2. **Clear Redis queue:**

   ```bash
   redis-cli FLUSHDB
   ```

3. **Restart the worker:**
   ```bash
   python start_celery_worker.py
   ```

## Best Practices

1. **Always check task status before revoking** - Make sure you're revoking the right task
2. **Use graceful revocation** - The enhanced task will save partial results
3. **Monitor worker health** - Use the stats command to check worker status
4. **Log important operations** - Keep track of what tasks you've stopped and why

## Troubleshooting

### Task Won't Stop

- Check if the worker is still running
- Try terminating the worker process directly
- Clear the Redis queue as a last resort

### Can't Find Task ID

- Use the list command to see all active tasks
- Check the logs for task IDs
- Look in your Redis database for task metadata

### Worker Not Responding

- Check worker logs
- Restart the worker process
- Verify Redis connection

### Tasks Not Showing in Active List (Redis/Homebrew Issue)

**Problem**: Tasks are running but don't appear in `inspect().active()` results.

**Cause**: This is a common issue with Celery's `inspect().active()` method when using Redis as the broker. The method doesn't always detect tasks that are in PROGRESS state.

**Solution**: The enhanced task management tools now check Redis directly for tasks in PROGRESS state:

```bash
# This will now show tasks from both inspect() and Redis
python task_manager.py list

# Or use the management command
python manage.py manage_tasks --action list
```

**Why this happens**:

- Celery's `inspect().active()` only shows tasks that are currently being executed by workers
- Tasks in PROGRESS state might not be detected if the worker is busy
- Redis stores task metadata separately from the active task list
- Multiple worker processes can cause confusion in task detection

**Workaround**: The enhanced tools now check both sources:

1. Celery's `inspect().active()` for truly active tasks
2. Redis metadata for tasks in PROGRESS state
3. Combined results show all running tasks
