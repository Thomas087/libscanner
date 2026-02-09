from django.db import models
from django.utils import timezone

# Create your models here.

class GovernmentDocument(models.Model):
    """
    Model to store government documents with their metadata.
    Uses link as unique identifier to prevent duplicates.
    """
    title = models.CharField(max_length=500, help_text="Title of the document")
    description = models.TextField(blank=True, null=True, help_text="Description of the document")
    summary = models.TextField(blank=True, null=True, help_text="Summary of the document content")
    full_page_text = models.TextField(blank=True, null=True, help_text="Full text content of the scraped page")
    link = models.URLField(max_length=2048, unique=True, help_text="URL to the document on the government website")
    date_updated = models.DateTimeField(help_text="Date when the document was last updated on the government website")
    is_animal_farming_project = models.BooleanField(default=False, help_text="Whether this document is related to an animal farming project")
    animal_type = models.CharField(max_length=100, blank=True, null=True, help_text="Type of animal if this document is related to an animal project")
    animal_number = models.IntegerField(blank=True, null=True, help_text="Number of animals if this document is related to an animal project")

    # Prefecture information
    prefecture_name = models.CharField(max_length=100, blank=True, null=True, help_text="Name of the prefecture where this document was found")
    prefecture_code = models.CharField(max_length=10, blank=True, null=True, help_text="Code of the prefecture")
    region_name = models.CharField(max_length=100, blank=True, null=True, help_text="Name of the region")
    
    created_at = models.DateTimeField(auto_now_add=True, help_text="When this record was created in our database")
    updated_at = models.DateTimeField(auto_now=True, help_text="When this record was last updated in our database")
    
    class Meta:
        ordering = ['-date_updated']
        verbose_name = "Government Document"
        verbose_name_plural = "Government Documents"
    
    def __str__(self):
        return self.title
    
    def is_recent(self, days=30):
        """Check if the document was updated recently (within specified days)"""
        return (timezone.now() - self.date_updated).days <= days


class NegativeKeyword(models.Model):
    """
    Model to store negative keywords that should be excluded from document searches.
    These keywords help filter out irrelevant documents during scraping.
    """
    keyword = models.CharField(
        max_length=200, 
        unique=True, 
        help_text="The negative keyword to exclude from searches"
    )
    created_at = models.DateTimeField(
        auto_now_add=True, 
        help_text="When this negative keyword was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True, 
        help_text="When this negative keyword was last updated"
    )
    
    class Meta:
        ordering = ['keyword']
        verbose_name = "Negative Keyword"
        verbose_name_plural = "Negative Keywords"
    
    def __str__(self):
        return self.keyword


class ScrapingTask(models.Model):
    """
    Model to track scraping tasks and their progress.
    """
    TASK_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROGRESS', 'In Progress'),
        ('SUCCESS', 'Completed Successfully'),
        ('FAILURE', 'Failed'),
        ('REVOKED', 'Cancelled'),
        ('RETRY', 'Retrying'),
    ]
    
    task_id = models.CharField(max_length=255, unique=True, help_text="Celery task ID")
    name = models.CharField(max_length=255, default="scrape_animal_keywords", help_text="Task name")
    status = models.CharField(max_length=20, choices=TASK_STATUS_CHOICES, default='PENDING', help_text="Current task status")
    
    # Task parameters
    keywords = models.JSONField(default=list, help_text="Keywords to search for")
    region_filter = models.CharField(max_length=100, blank=True, null=True, help_text="Region filter")
    prefecture_filter = models.CharField(max_length=100, blank=True, null=True, help_text="Prefecture filter")
    output_file = models.CharField(max_length=500, blank=True, null=True, help_text="Output file path")
    output_format = models.CharField(max_length=20, default='pretty', help_text="Output format")
    days_limit = models.IntegerField(default=30, help_text="Number of days to look back when scraping")
    
    # Progress tracking
    current_operation = models.IntegerField(default=0, help_text="Current operation number")
    total_operations = models.IntegerField(default=0, help_text="Total operations to perform")
    current_prefecture = models.CharField(max_length=100, blank=True, null=True, help_text="Currently processing prefecture")
    current_keyword = models.CharField(max_length=100, blank=True, null=True, help_text="Currently processing keyword")
    
    # Results
    total_items_found = models.IntegerField(default=0, help_text="Total items found")
    results_summary = models.JSONField(default=dict, blank=True, help_text="Summary of results")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, help_text="When the task was created")
    started_at = models.DateTimeField(blank=True, null=True, help_text="When the task started")
    completed_at = models.DateTimeField(blank=True, null=True, help_text="When the task completed")
    last_updated = models.DateTimeField(auto_now=True, help_text="When the task was last updated")
    
    # Error handling
    error_message = models.TextField(blank=True, null=True, help_text="Error message if task failed")
    traceback = models.TextField(blank=True, null=True, help_text="Error traceback if task failed")
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Scraping Task"
        verbose_name_plural = "Scraping Tasks"
    
    def __str__(self):
        return f"{self.name} - {self.task_id} ({self.status})"
    
    @property
    def progress_percentage(self):
        """Calculate progress percentage."""
        if self.total_operations == 0:
            return 0
        return round((self.current_operation / self.total_operations) * 100, 2)
    
    @property
    def duration(self):
        """Calculate task duration."""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        elif self.started_at:
            return timezone.now() - self.started_at
        return None
    
    def update_progress(self, current, total, prefecture=None, keyword=None):
        """Update task progress."""
        self.current_operation = current
        self.total_operations = total
        if prefecture:
            self.current_prefecture = prefecture
        if keyword:
            self.current_keyword = keyword
        self.status = 'PROGRESS'
        self.save()
    
    def mark_completed(self, results_summary=None, total_items=0):
        """Mark task as completed."""
        self.status = 'SUCCESS'
        self.completed_at = timezone.now()
        if results_summary:
            self.results_summary = results_summary
        self.total_items_found = total_items
        self.save()
    
    def mark_failed(self, error_message=None, traceback=None):
        """Mark task as failed."""
        self.status = 'FAILURE'
        self.completed_at = timezone.now()
        if error_message:
            self.error_message = error_message
        if traceback:
            self.traceback = traceback
        self.save()
    
    def mark_revoked(self):
        """Mark task as revoked."""
        self.status = 'REVOKED'
        self.completed_at = timezone.now()
        self.save()
    
    def force_stop(self):
        """Force stop a running task by revoking it and killing the worker if necessary."""
        from celery import current_app
        import os
        import signal
        import subprocess
        
        try:
            # First, try to revoke the task gracefully
            current_app.control.revoke(self.task_id, terminate=True)
            
            # Wait a moment for graceful shutdown
            import time
            time.sleep(2)
            
            # Check if task is still running by looking for worker processes
            try:
                # Get active tasks to see if our task is still there
                inspect = current_app.control.inspect()
                active_tasks = inspect.active()
                
                task_still_running = False
                if active_tasks:
                    for worker, tasks in active_tasks.items():
                        for task in tasks:
                            if task.get('id') == self.task_id:
                                task_still_running = True
                                break
                
                # If task is still running, we need to be more aggressive
                if task_still_running:
                    # Try to shutdown workers gracefully first
                    current_app.control.shutdown()
                    time.sleep(3)
                    
                    # If still running, find and kill worker processes
                    try:
                        # Find Celery worker processes
                        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
                        lines = result.stdout.split('\n')
                        
                        celery_pids = []
                        for line in lines:
                            if 'celery' in line and 'worker' in line and 'libscanner' in line:
                                parts = line.split()
                                if len(parts) > 1:
                                    try:
                                        pid = int(parts[1])
                                        celery_pids.append(pid)
                                    except (ValueError, IndexError):
                                        continue
                        
                        # Kill worker processes if found
                        for pid in celery_pids:
                            try:
                                os.kill(pid, signal.SIGTERM)
                                time.sleep(1)
                                # If still running, force kill
                                try:
                                    os.kill(pid, signal.SIGKILL)
                                except ProcessLookupError:
                                    pass  # Process already dead
                            except ProcessLookupError:
                                pass  # Process already dead
                                
                    except Exception:
                        # If we can't kill workers, at least mark the task as force-stopped
                        pass
                        
            except Exception:
                # If inspection fails, assume we need to be more aggressive
                pass
            
            # Mark as force-stopped
            self.status = 'REVOKED'
            self.completed_at = timezone.now()
            self.error_message = "Task force-stopped by admin"
            self.save()
            
            return True
            
        except Exception as e:
            # Even if we can't stop the task gracefully, mark it as revoked
            self.status = 'REVOKED'
            self.completed_at = timezone.now()
            self.error_message = f"Task force-stopped with error: {str(e)}"
            self.save()
            return False


class ScrapingTaskResult(models.Model):
    """
    Model to store individual results from scraping tasks.
    """
    task = models.ForeignKey(ScrapingTask, on_delete=models.CASCADE, related_name='results', help_text="Associated scraping task")
    prefecture_name = models.CharField(max_length=100, help_text="Name of the prefecture")
    region_name = models.CharField(max_length=100, help_text="Name of the region")
    keyword = models.CharField(max_length=100, help_text="Keyword that was searched")
    items_found = models.IntegerField(default=0, help_text="Number of items found for this keyword/prefecture combination")
    created_at = models.DateTimeField(auto_now_add=True, help_text="When this result was created")
    
    class Meta:
        ordering = ['-items_found']
        verbose_name = "Scraping Task Result"
        verbose_name_plural = "Scraping Task Results"
        unique_together = ['task', 'prefecture_name', 'keyword']
    
    def __str__(self):
        return f"{self.task.name} - {self.prefecture_name} - {self.keyword} ({self.items_found} items)"
