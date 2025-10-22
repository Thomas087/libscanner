"""
Management command to add negative keywords.
"""
from django.core.management.base import BaseCommand
from scraper.models import NegativeKeyword


class Command(BaseCommand):
    help = 'Add a negative keyword to filter out documents'

    def add_arguments(self, parser):
        parser.add_argument('keyword', type=str, help='The negative keyword to add')
        parser.add_argument('--force', action='store_true', help='Force update if keyword already exists')

    def handle(self, *args, **options):
        keyword = options['keyword']
        force = options['force']
        
        try:
            # Check if keyword already exists
            existing_keyword = NegativeKeyword.objects.filter(keyword=keyword).first()
            
            if existing_keyword and not force:
                self.stdout.write(
                    self.style.WARNING(f'Negative keyword "{keyword}" already exists. Use --force to update.')
                )
                return
            
            if existing_keyword and force:
                existing_keyword.save()  # Update timestamp
                self.stdout.write(
                    self.style.SUCCESS(f'Updated existing negative keyword: "{keyword}"')
                )
            else:
                NegativeKeyword.objects.create(keyword=keyword)
                self.stdout.write(
                    self.style.SUCCESS(f'Added new negative keyword: "{keyword}"')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error adding negative keyword: {e}')
            )
