"""
Django management command to start a scraping task for admin testing.
"""
import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from scraper.constants import ANIMAL_KEYWORDS
from scraper.models import ScrapingTask
from scraper.tasks import scrape_animal_keywords_enhanced_task

logger = logging.getLogger('scraper')


class Command(BaseCommand):
    help = 'Start a scraping task for admin testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--keywords',
            type=str,
            nargs='+',
            default=None,
            help='Keywords to search for (default: first two animal keywords: bovin, porcin)'
        )
        parser.add_argument(
            '--region',
            type=str,
            help='Filter by specific region'
        )
        parser.add_argument(
            '--prefecture',
            type=str,
            help='Filter by specific prefecture'
        )
        parser.add_argument(
            '--output',
            type=str,
            help='Output file path'
        )

    def handle(self, *args, **options):
        keywords = options['keywords'] or list(ANIMAL_KEYWORDS[:2])
        region_filter = options.get('region')
        prefecture_filter = options.get('prefecture')
        output_file = options.get('output')
        
        self.stdout.write("Creating scraping task...")
        
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
