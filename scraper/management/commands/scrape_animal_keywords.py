"""
Django management command to scrape all prefecture government websites for animal-related keywords.
"""
import json
import logging
from django.core.management.base import BaseCommand, CommandError
from scraper.scraper import scrape_all_results
from scraper.constants import PREFECTURES, get_prefectures_by_region, get_all_regions

logger = logging.getLogger('scraper')


class Command(BaseCommand):
    help = 'Scrape all prefecture government websites for animal-related keywords'

    # Define the keywords to search for
    ANIMAL_KEYWORDS = [
        "bovin",
        "porcin",
        "volaille",
        "poules",
        "pondeuses",
        "poulets"
    ]

    def add_arguments(self, parser):
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
            '--keywords',
            type=str,
            nargs='+',
            help='Custom keywords to search for (overrides default livestock keywords)'
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
        parser.add_argument(
            '--list-keywords',
            action='store_true',
            help='List all default animal keywords and exit'
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

        if options['list_keywords']:
            self.stdout.write("Default animal keywords:")
            for i, keyword in enumerate(self.ANIMAL_KEYWORDS, 1):
                self.stdout.write(f"  {i}. {keyword}")
            return

        # Determine keywords to use
        keywords = options.get('keywords') or self.ANIMAL_KEYWORDS
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

        self.stdout.write(f"Starting to scrape {len(prefectures_to_scrape)} prefecture(s) for {len(keywords)} keyword(s)")
        self.stdout.write(f"Keywords: {', '.join(keywords)}")
        logger.info(f"Starting scraping process - {len(prefectures_to_scrape)} prefectures, {len(keywords)} keywords")
        
        all_results = []
        results_by_keyword = {}
        results_by_prefecture = {}
        total_operations = len(prefectures_to_scrape) * len(keywords)
        current_operation = 0

        try:
            for keyword in keywords:
                self.stdout.write(f"\n{'='*60}")
                self.stdout.write(f"SEARCHING FOR: {keyword.upper()}")
                self.stdout.write(f"{'='*60}")
                
                keyword_results = []
                keyword_prefecture_results = {}
                
                for prefecture in prefectures_to_scrape:
                    current_operation += 1
                    progress = f"[{current_operation}/{total_operations}]"
                    
                    self.stdout.write(f"\n{progress} Scraping {prefecture['name']} ({prefecture['region']}) - {prefecture['domain']}")
                    self.stdout.write(f"Keyword: {keyword}")
                    
                    try:
                        logger.info(f"Starting scrape for {prefecture['name']} with keyword '{keyword}'")
                        # Scrape all results for this prefecture and keyword
                        results = scrape_all_results(prefecture['domain'], keyword)
                        
                        if results:
                            keyword_results.extend(results)
                            keyword_prefecture_results[prefecture['name']] = {
                                'prefecture': prefecture,
                                'results': results,
                                'count': len(results)
                            }
                            logger.info(f"Successfully scraped {len(results)} items from {prefecture['name']}")
                            self.stdout.write(
                                self.style.SUCCESS(f'  ✓ Found {len(results)} items')
                            )
                        else:
                            logger.warning(f"No results found for {prefecture['name']} with keyword '{keyword}'")
                            self.stdout.write(
                                self.style.WARNING('  ⚠ No results found')
                            )
                            keyword_prefecture_results[prefecture['name']] = {
                                'prefecture': prefecture,
                                'results': [],
                                'count': 0
                            }
                            
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f'  ✗ Error scraping {prefecture["name"]}: {e}')
                        )
                        keyword_prefecture_results[prefecture['name']] = {
                            'prefecture': prefecture,
                            'results': [],
                            'count': 0,
                            'error': str(e)
                        }
                        continue

                # Store results for this keyword
                results_by_keyword[keyword] = {
                    'total_items': len(keyword_results),
                    'prefectures': keyword_prefecture_results,
                    'all_results': keyword_results
                }
                all_results.extend(keyword_results)

            # Display comprehensive summary
            self.stdout.write(f"\n" + "="*80)
            self.stdout.write(f"COMPREHENSIVE SCRAPING SUMMARY")
            self.stdout.write(f"="*80)
            self.stdout.write(f"Total prefectures scraped: {len(prefectures_to_scrape)}")
            self.stdout.write(f"Total keywords searched: {len(keywords)}")
            self.stdout.write(f"Total operations: {total_operations}")
            self.stdout.write(f"Total items found: {len(all_results)}")
            
            # Summary by keyword
            self.stdout.write(f"\n--- RESULTS BY KEYWORD ---")
            for keyword, data in results_by_keyword.items():
                self.stdout.write(f"{keyword}: {data['total_items']} items")
                
                # Show top prefectures for this keyword
                prefecture_counts = [(name, info['count']) for name, info in data['prefectures'].items()]
                prefecture_counts.sort(key=lambda x: x[1], reverse=True)
                
                self.stdout.write(f"  Top prefectures for '{keyword}':")
                for name, count in prefecture_counts[:5]:  # Show top 5
                    if count > 0:
                        self.stdout.write(f"    {name}: {count} items")

            # Summary by prefecture
            self.stdout.write(f"\n--- RESULTS BY PREFECTURE ---")
            for prefecture in prefectures_to_scrape:
                prefecture_name = prefecture['name']
                total_for_prefecture = 0
                keyword_breakdown = []
                
                for keyword, data in results_by_keyword.items():
                    if prefecture_name in data['prefectures']:
                        count = data['prefectures'][prefecture_name]['count']
                        total_for_prefecture += count
                        if count > 0:
                            keyword_breakdown.append(f"{keyword}: {count}")
                
                if total_for_prefecture > 0:
                    self.stdout.write(f"{prefecture_name}: {total_for_prefecture} total items")
                    if keyword_breakdown:
                        self.stdout.write(f"  Breakdown: {', '.join(keyword_breakdown)}")

            # Save or display results
            if output_format == 'json':
                output_data = json.dumps({
                    'summary': {
                        'total_prefectures': len(prefectures_to_scrape),
                        'total_keywords': len(keywords),
                        'total_operations': total_operations,
                        'total_items': len(all_results),
                        'keywords': keywords
                    },
                    'results_by_keyword': results_by_keyword,
                    'all_results': all_results
                }, indent=2, ensure_ascii=False)
            else:
                # Pretty format
                output_data = self._format_results_pretty(results_by_keyword, keywords)

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

    def _format_results_pretty(self, results_by_keyword, keywords):
        """Format results in a human-readable way."""
        output = []
        output.append("=" * 100)
        output.append("ANIMAL KEYWORDS SCRAPING RESULTS")
        output.append("=" * 100)
        
        for keyword, data in results_by_keyword.items():
            output.append(f"\n--- KEYWORD: {keyword.upper()} ---")
            output.append(f"Total items found: {data['total_items']}")
            
            # Show results by prefecture for this keyword
            for prefecture_name, prefecture_data in data['prefectures'].items():
                prefecture = prefecture_data['prefecture']
                results = prefecture_data['results']
                count = prefecture_data['count']
                
                if count > 0:
                    output.append(f"\n  {prefecture['name']} ({prefecture['region']}): {count} items")
                    
                    # Show first 3 items as examples
                    for i, item in enumerate(results[:3], 1):
                        output.append(f"    Item {i}:")
                        if 'title' in item:
                            output.append(f"      Title: {item['title']}")
                        if 'link' in item:
                            output.append(f"      Link: {item['link']}")
                        if 'description' in item:
                            output.append(f"      Description: {item['description'][:100]}...")
                    
                    if len(results) > 3:
                        output.append(f"    ... and {len(results) - 3} more items")
                else:
                    output.append(f"\n  {prefecture['name']} ({prefecture['region']}): No results")
        
        output.append("\n" + "=" * 100)
        return "\n".join(output)
