from django.db import models
from django.utils import timezone
import json

# Create your models here.

class GovernmentDocument(models.Model):
    """
    Model to store government documents with their metadata.
    Uses link as unique identifier to prevent duplicates.
    """
    title = models.CharField(max_length=500, help_text="Title of the document")
    description = models.TextField(blank=True, null=True, help_text="Description of the document")
    link = models.URLField(unique=True, help_text="URL to the document on the government website")
    date_updated = models.DateTimeField(help_text="Date when the document was last updated on the government website")
    is_icpe = models.BooleanField(default=False, help_text="Whether this document is related to ICPE (Installations Classées pour la Protection de l'Environnement)")
    
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
