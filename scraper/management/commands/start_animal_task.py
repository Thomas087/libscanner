"""
Django management command to start the default animal keywords scraping task.
"""
import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from scraper.models import ScrapingTask
from scraper.constants import ANIMAL_KEYWORDS
from scraper.tasks import scrape_animal_keywords_enhanced_task

logger = logging.getLogger('scraper')


class Command(BaseCommand):
    help = 'Start the default animal keywords scraping task'

    def add_arguments(self, parser):
        parser.add_argument(
            '--region',
            type=str,
            help='Filter by specific region (e.g., Bretagne)'
        )
        parser.add_argument(
            '--prefecture',
            type=str,
            help='Filter by specific prefecture (e.g., Morbihan)'
        )
        parser.add_argument(
            '--output',
            type=str,
            help='Output file path to save results'
        )

    def handle(self, *args, **options):
        keywords = list(ANIMAL_KEYWORDS)
        region_filter = options.get('region')
        prefecture_filter = options.get('prefecture')
        output_file = options.get('output')
        
        self.stdout.write("Starting animal keywords scraping task...")
        self.stdout.write(f"Keywords: {', '.join(keywords)}")
        
        if region_filter:
            self.stdout.write(f"Region filter: {region_filter}")
        if prefecture_filter:
            self.stdout.write(f"Prefecture filter: {prefecture_filter}")
        if output_file:
            self.stdout.write(f"Output file: {output_file}")
        
        # Create task record
        task = ScrapingTask.objects.create(
            keywords=keywords,
            region_filter=region_filter,
            prefecture_filter=prefecture_filter,
            output_file=output_file,
            output_format='pretty'
        )
        
        self.stdout.write(f"Task created with ID: {task.id}")
        
        # Start Celery task
        celery_task = scrape_animal_keywords_enhanced_task.delay(
            task_id=task.id,
            keywords=keywords,
            region_filter=region_filter,
            prefecture_filter=prefecture_filter,
            output_file=output_file,
            output_format='pretty'
        )
        
        # Update task record with Celery task ID
        task.task_id = celery_task.id
        task.started_at = timezone.now()
        task.save()
        
        self.stdout.write(f"Celery task started with ID: {celery_task.id}")
        self.stdout.write(f"Database task ID: {task.id}")
        self.stdout.write("You can monitor the task in Django admin at:")
        self.stdout.write("http://localhost:8000/admin/scraper/scrapingtask/")
        self.stdout.write("")
        self.stdout.write("Task is now running in the background...")
