"""
Celery tasks for the scraper app.
"""
import json
import logging
from celery import shared_task
from django.utils import timezone
from scraper.analysis import scrape_all_results
from scraper.constants import PREFECTURES, ANIMAL_KEYWORDS, get_prefectures_by_region
from scraper.models import ScrapingTask, ScrapingTaskResult
from scraper.utils import format_results_pretty

logger = logging.getLogger('scraper')


@shared_task(name='daily_animal_scraping_task')
def daily_animal_scraping_task():
    """
    Scheduled task that runs daily at 1am to scrape animal keywords.
    Scrapes documents from the last 2 days (current and previous day).
    
    This task is triggered by Celery Beat and reuses the enhanced scraping task.
    """
    logger.info("Starting daily scheduled animal scraping task")
    
    keywords = list(ANIMAL_KEYWORDS)

    # Scrape last 2 days (current and previous day)
    days_limit = 2
    
    # Create task record for tracking
    db_task = ScrapingTask.objects.create(
        name="daily_animal_scraping",
        keywords=keywords,
        output_format='pretty',
        days_limit=days_limit
    )
    
    logger.info(f"Created daily scraping task with ID: {db_task.id}, days_limit: {days_limit}")
    
    # Call the enhanced scraping task synchronously (we're already in a Celery task)
    result = scrape_animal_keywords_enhanced_task(
        task_id=db_task.id,
        keywords=keywords,
        output_format='pretty',
        days_limit=days_limit
    )
    
    logger.info(f"Daily scraping task completed: {result.get('status', 'UNKNOWN')}")
    return result


@shared_task(bind=True, name='scrape_animal_keywords_enhanced_task')
def scrape_animal_keywords_enhanced_task(self, task_id=None, keywords=None, region_filter=None, prefecture_filter=None, output_file=None, output_format='pretty', days_limit=30):
    """
    Enhanced Celery task to scrape animal keywords with database tracking.
    
    Args:
        task_id: Database task ID for tracking
        keywords: List of keywords to search for
        region_filter: Filter by specific region
        prefecture_filter: Filter by specific prefecture
        output_file: Optional output file path
        output_format: Output format ('json' or 'pretty')
        days_limit: Number of days to look back when scraping (default: 30)
    
    Returns:
        dict: Results of the scraping operation
    """
    if keywords is None:
        keywords = list(ANIMAL_KEYWORDS)
    
    # Get or create the database task record
    try:
        if task_id:
            db_task = ScrapingTask.objects.get(id=task_id)
        else:
            # Create a new task record
            db_task = ScrapingTask.objects.create(
                task_id=self.request.id,
                keywords=keywords,
                region_filter=region_filter,
                prefecture_filter=prefecture_filter,
                output_file=output_file,
                output_format=output_format,
                started_at=timezone.now()
            )
    except ScrapingTask.DoesNotExist:
        logger.error(f"Task record not found for ID: {task_id}")
        return {
            'status': 'FAILURE',
            'message': 'Task record not found',
            'error': 'Task record not found'
        }
    
    logger.info(f"Starting enhanced Celery task for scraping with {len(keywords)} keywords, days_limit={days_limit}")
    
    # Filter prefectures based on arguments
    prefectures_to_scrape = PREFECTURES.copy()
    
    if region_filter:
        prefectures_to_scrape = get_prefectures_by_region(region_filter)
        if not prefectures_to_scrape:
            error_msg = f'No prefectures found for region: {region_filter}'
            db_task.mark_failed(error_message=error_msg)
            raise ValueError(error_msg)
    
    if prefecture_filter:
        prefectures_to_scrape = [p for p in prefectures_to_scrape if p['name'].lower() == prefecture_filter.lower()]
        if not prefectures_to_scrape:
            error_msg = f'No prefecture found with name: {prefecture_filter}'
            db_task.mark_failed(error_message=error_msg)
            raise ValueError(error_msg)
    
    logger.info(f"Scraping {len(prefectures_to_scrape)} prefecture(s) for {len(keywords)} keyword(s)")

    # Track counts only, not full results (memory efficient)
    results_by_keyword = {}
    total_operations = len(prefectures_to_scrape) * len(keywords)
    current_operation = 0
    total_items_count = 0

    # Update total operations in database
    db_task.total_operations = total_operations
    db_task.save()

    try:
        for keyword in keywords:
            logger.info(f"Processing keyword: {keyword}")

            keyword_total_count = 0
            keyword_prefecture_results = {}

            for prefecture in prefectures_to_scrape:
                current_operation += 1
                progress = f"[{current_operation}/{total_operations}]"

                logger.info(f"{progress} Scraping {prefecture['name']} ({prefecture['region']}) - {prefecture['domain']}")
                logger.info(f"Keyword: {keyword}")

                try:
                    # Update progress in database
                    db_task.update_progress(
                        current=current_operation,
                        total=total_operations,
                        prefecture=prefecture['name'],
                        keyword=keyword
                    )

                    # Update task state for Celery progress tracking
                    self.update_state(
                        state='PROGRESS',
                        meta={
                            'current': current_operation,
                            'total': total_operations,
                            'prefecture': prefecture['name'],
                            'keyword': keyword,
                            'status': 'scraping'
                        }
                    )

                    logger.info(f"Starting scrape for {prefecture['name']} with keyword '{keyword}'")

                    # Get count from database before scraping
                    from scraper.models import GovernmentDocument
                    before_count = GovernmentDocument.objects.filter(
                        prefecture_name=prefecture['name']
                    ).count()

                    # Scrape and save to database (returns empty list to save memory)
                    scrape_all_results(prefecture['domain'], keyword, days_limit=days_limit)

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

                    logger.info(f"Successfully scraped {items_added} items from {prefecture['name']}")

                    # Save individual result to database
                    ScrapingTaskResult.objects.update_or_create(
                        task=db_task,
                        prefecture_name=prefecture['name'],
                        keyword=keyword,
                        defaults={
                            'region_name': prefecture['region'],
                            'items_found': items_added
                        }
                    )

                except Exception as e:
                    logger.error(f"Error scraping {prefecture['name']}: {e}")
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

        # Prepare final results (metadata only)
        final_results = {
            'summary': {
                'total_prefectures': len(prefectures_to_scrape),
                'total_keywords': len(keywords),
                'total_operations': total_operations,
                'total_items': total_items_count,
                'keywords': keywords
            },
            'results_by_keyword': results_by_keyword
        }
        
        # Save results to file if specified
        if output_file:
            if output_format == 'json':
                output_data = json.dumps(final_results, indent=2, ensure_ascii=False)
            else:
                # Pretty format
                output_data = format_results_pretty(results_by_keyword, keywords)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(output_data)
            logger.info(f"Results saved to {output_file}")
        
        # Mark task as completed in database
        db_task.mark_completed(
            results_summary=final_results['summary'],
            total_items=total_items_count
        )

        logger.info(f"Enhanced task completed successfully. Found {total_items_count} total items.")

        return {
            'status': 'SUCCESS',
            'message': f'Scraping completed successfully. Found {total_items_count} items.',
            'results': final_results,
            'task_id': db_task.id
        }
        
    except Exception as e:
        logger.error(f"Enhanced task failed with error: {e}")
        db_task.mark_failed(error_message=str(e))
        return {
            'status': 'FAILURE',
            'message': f'Task failed: {str(e)}',
            'error': str(e),
            'task_id': db_task.id
        }
