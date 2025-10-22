"""
Django management command to scrape all prefecture government websites.
"""
import json
from django.core.management.base import BaseCommand, CommandError
from scraper.scraper import scrape_all_results
from scraper.constants import PREFECTURES, get_prefectures_by_region, get_all_regions


class Command(BaseCommand):
    help = 'Scrape all prefecture government websites for keyword-related content'

    def add_arguments(self, parser):
        parser.add_argument(
            '--keyword',
            type=str,
            default='elevage',
            help='Search keyword (default: elevage)'
        )
        parser.add_argument(
            '--region',
            type=str,
            help='Filter by specific region (e.g., "Bretagne", "Île-de-France")'
        )
        parser.add_argument(
            '--prefecture',
            type=str,
            help='Filter by specific prefecture name (e.g., "Morbihan")'
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
        parser.add_argument(
            '--list-regions',
            action='store_true',
            help='List all available regions and exit'
        )
        parser.add_argument(
            '--list-prefectures',
            action='store_true',
            help='List all available prefectures and exit'
        )

    def handle(self, *args, **options):
        # Handle list commands
        if options['list_regions']:
            self.stdout.write("Available regions:")
            for region in get_all_regions():
                self.stdout.write(f"  - {region}")
            return

        if options['list_prefectures']:
            self.stdout.write("Available prefectures:")
            for prefecture in PREFECTURES:
                self.stdout.write(f"  - {prefecture['name']} ({prefecture['region']}) - {prefecture['domain']}")
            return

        keyword = options['keyword']
        region_filter = options.get('region')
        prefecture_filter = options.get('prefecture')
        output_file = options.get('output')
        output_format = options['format']

        # Filter prefectures based on arguments
        prefectures_to_scrape = PREFECTURES.copy()

        if region_filter:
            prefectures_to_scrape = get_prefectures_by_region(region_filter)
            if not prefectures_to_scrape:
                raise CommandError(f'No prefectures found for region: {region_filter}')

        if prefecture_filter:
            prefectures_to_scrape = [p for p in prefectures_to_scrape if p['name'].lower() == prefecture_filter.lower()]
            if not prefectures_to_scrape:
                raise CommandError(f'No prefecture found with name: {prefecture_filter}')

        self.stdout.write(f"Starting to scrape {len(prefectures_to_scrape)} prefecture(s) for keyword: {keyword}")
        
        all_results = []
        results_by_prefecture = {}

        try:
            for prefecture in prefectures_to_scrape:
                self.stdout.write(f"\nScraping {prefecture['name']} ({prefecture['region']}) - {prefecture['domain']}")
                
                try:
                    # Scrape all results for this prefecture
                    results = scrape_all_results(prefecture['domain'], keyword)
                    
                    if results:
                        all_results.extend(results)
                        results_by_prefecture[prefecture['name']] = {
                            'prefecture': prefecture,
                            'results': results,
                            'count': len(results)
                        }
                        self.stdout.write(
                            self.style.SUCCESS(f'  ✓ Found {len(results)} items')
                        )
                    else:
                        self.stdout.write(
                            self.style.WARNING('  ⚠ No results found')
                        )
                        
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'  ✗ Error scraping {prefecture["name"]}: {e}')
                    )
                    continue

            # Display summary
            self.stdout.write(f"\n" + "="*60)
            self.stdout.write(f"SCRAPING SUMMARY")
            self.stdout.write(f"="*60)
            self.stdout.write(f"Total prefectures scraped: {len(prefectures_to_scrape)}")
            self.stdout.write(f"Total items found: {len(all_results)}")
            
            for prefecture_name, data in results_by_prefecture.items():
                self.stdout.write(f"  {prefecture_name}: {data['count']} items")

            # Save or display results
            if output_format == 'json':
                output_data = json.dumps({
                    'summary': {
                        'total_prefectures': len(prefectures_to_scrape),
                        'total_items': len(all_results),
                        'keyword': keyword
                    },
                    'results_by_prefecture': results_by_prefecture,
                    'all_results': all_results
                }, indent=2, ensure_ascii=False)
            else:
                # Pretty format
                output_data = self._format_results_pretty(results_by_prefecture, keyword)

            # Display or save results
            if output_file:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(output_data)
                self.stdout.write(
                    self.style.SUCCESS(f'\nResults saved to {output_file}')
                )
            else:
                self.stdout.write(output_data)
                
        except Exception as e:
            raise CommandError(f'Error during scraping: {e}')

    def _format_results_pretty(self, results_by_prefecture, keyword):
        """Format results in a human-readable way."""
        output = []
        output.append("=" * 80)
        output.append(f"SCRAPING RESULTS FOR KEYWORD: {keyword.upper()}")
        output.append("=" * 80)
        
        for prefecture_name, data in results_by_prefecture.items():
            prefecture = data['prefecture']
            results = data['results']
            
            output.append(f"\n--- {prefecture['name']} ({prefecture['region']}) ---")
            output.append(f"Domain: {prefecture['domain']}")
            output.append(f"Items found: {len(results)}")
            
            for i, item in enumerate(results[:5], 1):  # Show first 5 items
                output.append(f"\n  Item {i}:")
                if 'title' in item:
                    output.append(f"    Title: {item['title']}")
                if 'link' in item:
                    output.append(f"    Link: {item['link']}")
                if 'description' in item:
                    output.append(f"    Description: {item['description']}")
            
            if len(results) > 5:
                output.append(f"    ... and {len(results) - 5} more items")
        
        output.append("\n" + "=" * 80)
        return "\n".join(output)
