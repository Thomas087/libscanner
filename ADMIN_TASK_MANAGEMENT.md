# Django Admin Task Management Interface

This guide explains how to use the new Django admin interface for managing scraping tasks.

## Overview

The Django admin now includes a comprehensive task management system that allows you to:

- **Launch scraping tasks** with custom parameters
- **Monitor real-time progress** with visual progress bars
- **Stop running tasks** with a single click
- **View detailed results** for each task
- **Track individual results** by prefecture and keyword

## Accessing the Admin Interface

1. **Start the Django development server:**

   ```bash
   python manage.py runserver
   ```

2. **Access the admin interface:**

   ```
   http://localhost:8000/admin/
   ```

3. **Navigate to Scraping Tasks:**
   - Go to "Scraper" section
   - Click on "Scraping tasks"

## Starting a New Task

### Method 1: Using the Admin Interface

1. **Go to the Scraping Tasks list page**
2. **Click "Start new scraping task"** (admin action)
3. **Fill in the form:**
   - **Keywords:** Comma-separated list (e.g., "bovin,porcin,volaille")
   - **Region filter:** Optional (e.g., "Bretagne")
   - **Prefecture filter:** Optional (e.g., "Morbihan")
   - **Output file:** Optional file path to save results
   - **Output format:** Choose "Pretty" or "JSON"
4. **Click "Start Task"**

### Method 2: Using Management Command

```bash
# Start a basic task
python manage.py start_admin_task

# Start with custom parameters
python manage.py start_admin_task --keywords bovin porcin --region Bretagne --output results.txt
```

## Monitoring Tasks

### Task List View

The main task list shows:

- **Task ID:** Unique identifier
- **Status:** Color-coded status (Pending, In Progress, Success, Failed, Cancelled)
- **Progress:** Visual progress bar with percentage
- **Operations:** Current operation / Total operations
- **Items Found:** Total items discovered
- **Duration:** How long the task has been running
- **Actions:** Stop button for running tasks

### Task Detail View

Click on any task to see:

- **Complete task information**
- **Real-time progress updates**
- **Current prefecture and keyword being processed**
- **Results summary**
- **Individual results by prefecture and keyword**
- **Error information (if any)**

### Status Colors

- 🟠 **Pending:** Task is queued but not started
- 🔵 **In Progress:** Task is currently running
- 🟢 **Success:** Task completed successfully
- 🔴 **Failed:** Task encountered an error
- ⚫ **Cancelled:** Task was stopped by user

## Stopping Tasks

### Method 1: Using the Admin Interface

1. **Find the running task** in the list
2. **Click the red "Stop" button** in the Actions column
3. **Confirm the action**

### Method 2: Using Management Commands

```bash
# Stop a specific task
python manage.py manage_tasks --action revoke --task-id <TASK_ID>

# Stop all tasks
python task_manager.py revoke-all
```

## Viewing Results

### Task Results

Each task shows:

- **Total items found**
- **Results by keyword**
- **Results by prefecture**
- **Individual result records**

### Individual Results

Navigate to "Scraping task results" to see:

- **Per-prefecture results**
- **Per-keyword results**
- **Item counts for each combination**
- **Filtering and search capabilities**

## Advanced Features

### Real-time Progress Updates

The admin interface automatically updates:

- **Progress percentage**
- **Current operation count**
- **Current prefecture being processed**
- **Current keyword being searched**
- **Total items found so far**

### Task History

All tasks are preserved with:

- **Complete execution history**
- **Parameters used**
- **Results obtained**
- **Error messages (if any)**
- **Execution times**

### Filtering and Search

Use the admin filters to:

- **Filter by status**
- **Filter by date range**
- **Search by task ID**
- **Search by prefecture**
- **Search by keyword**

## Database Models

### ScrapingTask

Tracks the main task information:

- Task parameters (keywords, filters, output settings)
- Progress tracking (current operation, total operations)
- Status and timestamps
- Results summary
- Error information

### ScrapingTaskResult

Tracks individual results:

- Per-prefecture results
- Per-keyword results
- Item counts
- Associated task

## API Endpoints

The admin interface provides JSON endpoints:

- **Task Progress:** `/admin/scraper/scrapingtask/task-progress/<task_id>/`
- **Start Task:** `/admin/scraper/scrapingtask/start-task/`
- **Stop Task:** `/admin/scraper/scrapingtask/stop-task/<task_id>/`

## Best Practices

### Before Starting a Task

1. **Check for running tasks** - Don't start multiple large tasks simultaneously
2. **Choose appropriate filters** - Use region/prefecture filters to limit scope
3. **Set reasonable keywords** - Start with a few keywords for testing
4. **Monitor system resources** - Large tasks can be resource-intensive

### During Task Execution

1. **Monitor progress regularly** - Check the admin interface periodically
2. **Watch for errors** - Failed tasks will show error messages
3. **Consider stopping if needed** - Use the stop button if the task is taking too long

### After Task Completion

1. **Review results** - Check the results summary and individual records
2. **Export data if needed** - Use the output file feature for large datasets
3. **Clean up old tasks** - Delete completed tasks to save space

## Troubleshooting

### Task Won't Start

- **Check Celery worker** - Ensure the worker is running
- **Check Redis connection** - Verify Redis is accessible
- **Check database** - Ensure migrations are applied

### Task Stuck in Progress

- **Check worker logs** - Look for error messages
- **Restart worker if needed** - Stop and restart the Celery worker
- **Use force stop** - Use the management commands to force stop

### No Results Found

- **Check keywords** - Ensure keywords are relevant
- **Check filters** - Verify region/prefecture filters are correct
- **Check network** - Ensure the scraper can access target websites

## Integration with Existing Tools

The admin interface works alongside the existing command-line tools:

- **Management commands** still work for automation
- **Task manager script** can be used for bulk operations
- **Celery monitoring** tools remain available
- **Redis inspection** tools are still functional

This provides a complete solution for both interactive and automated task management!
