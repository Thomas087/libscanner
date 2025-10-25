"""
Django management command to scrape all prefecture government websites for animal-related keywords.
"""
import json
import logging
from django.core.management.base import BaseCommand, CommandError
from scraper.analysis import scrape_all_results
from scraper.constants import PREFECTURES, get_prefectures_by_region, get_all_regions
from scraper.utils import format_results_pretty

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
        parser.add_argument(
            '--async',
            action='store_true',
            help='Run scraping asynchronously using Celery task queue'
        )
        parser.add_argument(
            '--task-id',
            type=str,
            help='Check status of a running task (requires --async)'
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

        # Handle task status check
        if options.get('task_id'):
            return self._check_task_status(options['task_id'])

        # Determine keywords to use
        keywords = options.get('keywords') or self.ANIMAL_KEYWORDS
        region_filter = options.get('region')
        prefecture_filter = options.get('prefecture')
        output_file = options.get('output')
        output_format = options['format']
        use_async = options.get('async', False)

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

        if use_async:
            raise CommandError('Async mode is no longer supported. Please use the Django admin interface to start async scraping tasks.')
        else:
            return self._run_sync_scraping(keywords, region_filter, prefecture_filter, output_file, output_format, prefectures_to_scrape)


    def _run_sync_scraping(self, keywords, region_filter, prefecture_filter, output_file, output_format, prefectures_to_scrape):
        """
        Run scraping synchronously with memory-efficient approach.

        Note: scrape_all_results now saves directly to database and returns empty list
        to save memory. We track counts instead of accumulating all data.
        """
        self.stdout.write(f"Starting to scrape {len(prefectures_to_scrape)} prefecture(s) for {len(keywords)} keyword(s)")
        self.stdout.write(f"Keywords: {', '.join(keywords)}")
        logger.info(f"Starting scraping process - {len(prefectures_to_scrape)} prefectures, {len(keywords)} keywords")

        # Track counts only, not full results (memory efficient)
        results_by_keyword = {}
        total_operations = len(prefectures_to_scrape) * len(keywords)
        current_operation = 0
        total_items_count = 0

        try:
            for keyword in keywords:
                self.stdout.write(f"\n{'='*60}")
                self.stdout.write(f"SEARCHING FOR: {keyword.upper()}")
                self.stdout.write(f"{'='*60}")

                keyword_total_count = 0
                keyword_prefecture_results = {}

                for prefecture in prefectures_to_scrape:
                    current_operation += 1
                    progress = f"[{current_operation}/{total_operations}]"

                    self.stdout.write(f"\n{progress} Scraping {prefecture['name']} ({prefecture['region']}) - {prefecture['domain']}")
                    self.stdout.write(f"Keyword: {keyword}")

                    try:
                        logger.info(f"Starting scrape for {prefecture['name']} with keyword '{keyword}'")

                        # Get count from database before scraping
                        from scraper.models import GovernmentDocument
                        before_count = GovernmentDocument.objects.filter(
                            prefecture_name=prefecture['name']
                        ).count()

                        # Scrape and save to database (returns empty list to save memory)
                        scrape_all_results(prefecture['domain'], keyword)

                        # Get count after scraping to determine new items
                        after_count = GovernmentDocument.objects.filter(
                            prefecture_name=prefecture['name']
                        ).count()

                        items_added = after_count - before_count
                        keyword_total_count += items_added
                        total_items_count += items_added

                        # Store only metadata, not full results
                        keyword_prefecture_results[prefecture['name']] = {
                            'prefecture': prefecture,
                            'count': items_added
                        }

                        if items_added > 0:
                            logger.info(f"Successfully scraped {items_added} items from {prefecture['name']}")
                            self.stdout.write(
                                self.style.SUCCESS(f'  ✓ Found {items_added} items')
                            )
                        else:
                            logger.warning(f"No new items found for {prefecture['name']} with keyword '{keyword}'")
                            self.stdout.write(
                                self.style.WARNING('  ⚠ No new items found')
                            )

                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f'  ✗ Error scraping {prefecture["name"]}: {e}')
                        )
                        keyword_prefecture_results[prefecture['name']] = {
                            'prefecture': prefecture,
                            'count': 0,
                            'error': str(e)
                        }
                        continue

                # Store only metadata for this keyword
                results_by_keyword[keyword] = {
                    'total_items': keyword_total_count,
                    'prefectures': keyword_prefecture_results
                }

            # Display comprehensive summary
            self.stdout.write("\n" + "="*80)
            self.stdout.write("COMPREHENSIVE SCRAPING SUMMARY")
            self.stdout.write("="*80)
            self.stdout.write(f"Total prefectures scraped: {len(prefectures_to_scrape)}")
            self.stdout.write(f"Total keywords searched: {len(keywords)}")
            self.stdout.write(f"Total operations: {total_operations}")
            self.stdout.write(f"Total items found: {total_items_count}")

            # Summary by keyword
            self.stdout.write("\n--- RESULTS BY KEYWORD ---")
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
            self.stdout.write("\n--- RESULTS BY PREFECTURE ---")
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

            # Save or display results (metadata only, not full data)
            if output_format == 'json':
                output_data = json.dumps({
                    'summary': {
                        'total_prefectures': len(prefectures_to_scrape),
                        'total_keywords': len(keywords),
                        'total_operations': total_operations,
                        'total_items': total_items_count,
                        'keywords': keywords
                    },
                    'results_by_keyword': results_by_keyword
                }, indent=2, ensure_ascii=False)
            else:
                # Pretty format (metadata only)
                output_data = format_results_pretty(results_by_keyword, keywords)

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

    def _check_task_status(self, task_id):
        """Check the status of a running task."""
        from celery.result import AsyncResult
        
        result = AsyncResult(task_id)
        
        if result.state == 'PENDING':
            self.stdout.write(f"Task {task_id} is pending...")
        elif result.state == 'PROGRESS':
            meta = result.info
            self.stdout.write(f"Task {task_id} is in progress:")
            self.stdout.write(f"  Progress: {meta.get('current', 0)}/{meta.get('total', 0)}")
            self.stdout.write(f"  Current: {meta.get('prefecture', 'Unknown')} - {meta.get('keyword', 'Unknown')}")
            self.stdout.write(f"  Status: {meta.get('status', 'Unknown')}")
        elif result.state == 'SUCCESS':
            self.stdout.write(f"Task {task_id} completed successfully!")
            result_data = result.result
            if isinstance(result_data, dict):
                self.stdout.write(f"  Message: {result_data.get('message', 'No message')}")
                if 'results' in result_data:
                    results = result_data['results']
                    if 'summary' in results:
                        summary = results['summary']
                        self.stdout.write(f"  Total items found: {summary.get('total_items', 0)}")
                        self.stdout.write(f"  Prefectures scraped: {summary.get('total_prefectures', 0)}")
                        self.stdout.write(f"  Keywords searched: {summary.get('total_keywords', 0)}")
        elif result.state == 'FAILURE':
            self.stdout.write(f"Task {task_id} failed!")
            self.stdout.write(f"  Error: {result.info}")
        else:
            self.stdout.write(f"Task {task_id} state: {result.state}")
            if result.info:
                self.stdout.write(f"  Info: {result.info}")
        
        return result.state
