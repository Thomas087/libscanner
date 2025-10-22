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
