"""
Django management command to scrape the Morbihan government website.
"""
import json
from django.core.management.base import BaseCommand, CommandError
from scraper.scraper import scrape_url
from scraper.constants import PREFECTURES, get_all_domains


class Command(BaseCommand):
    help = 'Scrape government websites for keyword-related content'

    def add_arguments(self, parser):
        parser.add_argument(
            '--domain',
            type=str,
            default='morbihan.gouv.fr',
            help='Domain name to scrape (default: morbihan.gouv.fr)'
        )
        parser.add_argument(
            '--keyword',
            type=str,
            default='elevage',
            help='Search keyword (default: elevage)'
        )
        parser.add_argument(
            '--offset',
            type=int,
            default=0,
            help='Pagination offset (default: 0)'
        )
        parser.add_argument(
            '--output',
            type=str,
            help='Output file to save results (optional)'
        )
        parser.add_argument(
            '--format',
            type=str,
            choices=['json', 'pretty'],
            default='pretty',
            help='Output format (json or pretty)'
        )

    def handle(self, *args, **options):
        domain = options['domain']
        keyword = options['keyword']
        offset = options['offset']
        output_file = options.get('output')
        output_format = options['format']
        
        # Construct URL for display
        if offset > 0:
            url = f"https://www.{domain}/contenu/recherche/(offset)/{offset}/(searchtext)/{keyword}?SearchText={keyword}"
        else:
            url = f"https://www.{domain}/contenu/recherche/(searchtext)/{keyword}?SearchText={keyword}"
        
        self.stdout.write(f"Starting to scrape: {url}")
        self.stdout.write(f"Domain: {domain}, Keyword: {keyword}, Offset: {offset}")
        
        try:
            # Scrape the URL
            results = scrape_url(domain, keyword, offset)
            
            if not results:
                self.stdout.write(
                    self.style.WARNING('No results found. The website structure might have changed.')
                )
                return
            
            # Display results
            self.stdout.write(
                self.style.SUCCESS(f'Successfully scraped {len(results)} items')
            )
            
            if output_format == 'json':
                output_data = json.dumps(results, indent=2, ensure_ascii=False)
            else:
                # Pretty format
                output_data = self._format_results_pretty(results)
            
            # Display or save results
            if output_file:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(output_data)
                self.stdout.write(
                    self.style.SUCCESS(f'Results saved to {output_file}')
                )
            else:
                self.stdout.write(output_data)
                
        except Exception as e:
            raise CommandError(f'Error during scraping: {e}')

    def _format_results_pretty(self, results):
        """Format results in a human-readable way."""
        output = []
        output.append("=" * 80)
        output.append("SCRAPING RESULTS")
        output.append("=" * 80)
        
        for i, item in enumerate(results, 1):
            output.append(f"\n--- Item {i} ---")
            
            if 'title' in item:
                output.append(f"Title: {item['title']}")
            
            if 'link' in item:
                output.append(f"Link: {item['link']}")
            
            if 'description' in item:
                output.append(f"Description: {item['description']}")
            
            if 'date' in item:
                output.append(f"Date: {item['date']}")
            
            if 'metadata' in item:
                output.append("Metadata:")
                for key, value in item['metadata'].items():
                    if isinstance(value, list):
                        output.append(f"  {key}: {', '.join(value)}")
                    else:
                        output.append(f"  {key}: {value}")
        
        output.append("\n" + "=" * 80)
        return "\n".join(output)
