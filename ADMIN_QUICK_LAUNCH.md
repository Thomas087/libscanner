# Django Admin Quick Launch Guide

This guide explains how to use the new quick launch features in the Django admin interface for starting scraping tasks.

## 🚀 Quick Launch Features

The Django admin now includes several ways to quickly start scraping tasks:

### 1. **Quick Launch Buttons** (Main Interface)

When you visit the Scraping Tasks admin page (`/admin/scraper/scrapingtask/`), you'll see:

- **🚀 Start New Task** - Opens the custom task configuration form
- **🐄 Start Animal Keywords Scraping** - Starts the default animal keywords task immediately
- **📊 View Results** - Navigate to the results page

### 2. **Admin Actions** (Dropdown Menu)

In the Scraping Tasks list, use the "Action" dropdown to:

- **Start new scraping task** - Opens the custom task form
- **🐄 Start Animal Keywords Scraping** - Starts the default task

### 3. **Command Line Interface**

Use the new management command:

```bash
# Start default animal keywords task
python manage.py start_animal_task

# Start with region filter
python manage.py start_animal_task --region Bretagne

# Start with prefecture filter
python manage.py start_animal_task --prefecture Morbihan

# Start with output file
python manage.py start_animal_task --output results.txt
```

## 🎯 Default Animal Keywords Task

The "Animal Keywords Scraping" task uses these default keywords:

- **bovin** (cattle)
- **porcin** (pigs)
- **volaille** (poultry)
- **poules** (hens)
- **pondeuses** (laying hens)
- **poulets** (chickens)

This task will:

- Search all prefectures by default
- Use the enhanced task with database tracking
- Show real-time progress in the admin interface
- Save individual results by prefecture and keyword

## 🔧 How to Use

### Method 1: Admin Interface (Recommended)

1. **Go to Django Admin:**

   ```
   http://localhost:8000/admin/scraper/scrapingtask/
   ```

2. **Click "🐄 Start Animal Keywords Scraping"** button

3. **Monitor Progress:**

   - Watch the progress bar update in real-time
   - See current prefecture and keyword being processed
   - View total items found

4. **Stop if Needed:**
   - Click the red "Stop" button if you need to cancel

### Method 2: Admin Actions

1. **Go to the Scraping Tasks list**
2. **Select "🐄 Start Animal Keywords Scraping"** from the Action dropdown
3. **Click "Go"**

### Method 3: Command Line

```bash
# Start the task
python manage.py start_animal_task

# Monitor in admin
# Visit: http://localhost:8000/admin/scraper/scrapingtask/
```

## 📊 Monitoring Progress

### Real-time Updates

The admin interface shows:

- **Progress Bar** - Visual progress with percentage
- **Current Operation** - e.g., "15/576"
- **Current Prefecture** - Which prefecture is being processed
- **Current Keyword** - Which keyword is being searched
- **Total Items Found** - Running count of discovered items

### Status Indicators

- 🟠 **Pending** - Task is queued
- 🔵 **In Progress** - Task is running
- 🟢 **Success** - Task completed successfully
- 🔴 **Failed** - Task encountered an error
- ⚫ **Cancelled** - Task was stopped

### Task Details

Click on any task to see:

- **Complete task information**
- **Parameters used**
- **Results summary**
- **Individual results by prefecture/keyword**
- **Error information (if any)**

## 🛑 Stopping Tasks

### From Admin Interface

1. **Find the running task** in the list
2. **Click the red "Stop" button**
3. **Task will gracefully stop** and save partial results

### From Command Line

```bash
# Stop specific task
python manage.py manage_tasks --action revoke --task-id <TASK_ID>

# Stop all tasks
python task_manager.py revoke-all
```

## 📈 Viewing Results

### Task Results

Each completed task shows:

- **Total items found**
- **Results by keyword**
- **Results by prefecture**
- **Execution time**

### Individual Results

Navigate to "Scraping task results" to see:

- **Per-prefecture results**
- **Per-keyword results**
- **Item counts for each combination**

## 🔍 Advanced Usage

### Custom Parameters

For more control, use the "Start New Task" button to configure:

- **Custom keywords**
- **Region filters**
- **Prefecture filters**
- **Output file settings**
- **Output format (JSON/Pretty)**

### Filtering Tasks

Use the admin filters to:

- **Filter by status**
- **Filter by date**
- **Search by task ID**
- **Search by prefecture**

### Bulk Operations

Use admin actions for:

- **Starting multiple tasks**
- **Stopping multiple tasks**
- **Viewing task details**

## 🚨 Important Notes

### Before Starting

1. **Check for running tasks** - Don't start multiple large tasks
2. **Monitor system resources** - Large tasks can be resource-intensive
3. **Choose appropriate scope** - Use filters to limit the search area

### During Execution

1. **Monitor progress regularly** - Check the admin interface
2. **Watch for errors** - Failed tasks will show error messages
3. **Consider stopping if needed** - Use the stop button if taking too long

### After Completion

1. **Review results** - Check the results summary
2. **Export data if needed** - Use the output file feature
3. **Clean up old tasks** - Delete completed tasks to save space

## 🎉 Benefits

The new quick launch features provide:

- **One-click task starting** - No need to configure parameters
- **Real-time monitoring** - See progress as it happens
- **Easy task management** - Start, stop, and monitor from one interface
- **Detailed results** - Individual results by prefecture and keyword
- **Error handling** - Clear error messages and recovery options

This makes the scraping system much more user-friendly and accessible for both technical and non-technical users!
