"""
Management command to clean up documents containing negative keywords.
"""
from django.core.management.base import BaseCommand
from scraper.scraper import remove_documents_with_negative_keywords


class Command(BaseCommand):
    help = 'Remove documents from the database that contain negative keywords'

    def handle(self, *args, **options):
        self.stdout.write('Starting cleanup of documents with negative keywords...')
        self.stdout.write('This will remove ALL documents containing negative keywords, regardless of age.')
        
        removed_count = remove_documents_with_negative_keywords(days=None)
        
        if removed_count > 0:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully removed {removed_count} documents containing negative keywords')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('No documents containing negative keywords were found')
            )
