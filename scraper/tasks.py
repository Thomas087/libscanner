"""
Celery tasks for the scraper app.
"""
import json
import logging
from celery import shared_task
from django.conf import settings
from django.utils import timezone
from scraper.scraper import scrape_all_results
from scraper.constants import PREFECTURES, get_prefectures_by_region
from scraper.models import ScrapingTask, ScrapingTaskResult

logger = logging.getLogger('scraper')


@shared_task(bind=True, name='scrape_animal_keywords_task')
def scrape_animal_keywords_task(self, keywords=None, region_filter=None, prefecture_filter=None, output_file=None, output_format='pretty'):
    """
    Celery task to scrape animal keywords from prefecture websites.
    
    Args:
        keywords: List of keywords to search for
        region_filter: Filter by specific region
        prefecture_filter: Filter by specific prefecture
        output_file: Optional output file path
        output_format: Output format ('json' or 'pretty')
    
    Returns:
        dict: Results of the scraping operation
    """
    # Default animal keywords if none provided
    if keywords is None:
        keywords = [
            "bovin",
            "porcin", 
            "volaille",
            "poules",
            "pondeuses",
            "poulets"
        ]
    
    logger.info(f"Starting Celery task for scraping with {len(keywords)} keywords")
    
    # Filter prefectures based on arguments
    prefectures_to_scrape = PREFECTURES.copy()
    
    if region_filter:
        prefectures_to_scrape = get_prefectures_by_region(region_filter)
        if not prefectures_to_scrape:
            raise ValueError(f'No prefectures found for region: {region_filter}')
    
    if prefecture_filter:
        prefectures_to_scrape = [p for p in prefectures_to_scrape if p['name'].lower() == prefecture_filter.lower()]
        if not prefectures_to_scrape:
            raise ValueError(f'No prefecture found with name: {prefecture_filter}')
    
    logger.info(f"Scraping {len(prefectures_to_scrape)} prefecture(s) for {len(keywords)} keyword(s)")
    
    all_results = []
    results_by_keyword = {}
    results_by_prefecture = {}
    total_operations = len(prefectures_to_scrape) * len(keywords)
    current_operation = 0
    
    try:
        for keyword in keywords:
            logger.info(f"Processing keyword: {keyword}")
            
            keyword_results = []
            keyword_prefecture_results = {}
            
            for prefecture in prefectures_to_scrape:
                current_operation += 1
                progress = f"[{current_operation}/{total_operations}]"
                
                logger.info(f"{progress} Scraping {prefecture['name']} ({prefecture['region']}) - {prefecture['domain']}")
                logger.info(f"Keyword: {keyword}")
                
                try:
                    # Check if task has been revoked (simplified check)
                    # Note: is_aborted() method may not be available in all Celery versions
                    # We'll skip this check for now to avoid errors
                    
                    # Update task state for progress tracking
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
                    else:
                        logger.warning(f"No results found for {prefecture['name']} with keyword '{keyword}'")
                        keyword_prefecture_results[prefecture['name']] = {
                            'prefecture': prefecture,
                            'results': [],
                            'count': 0
                        }
                        
                except Exception as e:
                    logger.error(f"Error scraping {prefecture['name']}: {e}")
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
        
        # Prepare final results
        final_results = {
            'summary': {
                'total_prefectures': len(prefectures_to_scrape),
                'total_keywords': len(keywords),
                'total_operations': total_operations,
                'total_items': len(all_results),
                'keywords': keywords
            },
            'results_by_keyword': results_by_keyword,
            'all_results': all_results
        }
        
        # Save results to file if specified
        if output_file:
            if output_format == 'json':
                output_data = json.dumps(final_results, indent=2, ensure_ascii=False)
            else:
                # Pretty format
                output_data = _format_results_pretty(results_by_keyword, keywords)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(output_data)
            logger.info(f"Results saved to {output_file}")
        
        logger.info(f"Task completed successfully. Found {len(all_results)} total items.")
        
        return {
            'status': 'SUCCESS',
            'message': f'Scraping completed successfully. Found {len(all_results)} items.',
            'results': final_results
        }
        
    except Exception as e:
        logger.error(f"Task failed with error: {e}")
        return {
            'status': 'FAILURE',
            'message': f'Task failed: {str(e)}',
            'error': str(e)
        }


def _format_results_pretty(results_by_keyword, keywords):
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


@shared_task(bind=True, name='scrape_animal_keywords_enhanced_task')
def scrape_animal_keywords_enhanced_task(self, task_id=None, keywords=None, region_filter=None, prefecture_filter=None, output_file=None, output_format='pretty'):
    """
    Enhanced Celery task to scrape animal keywords with database tracking.
    
    Args:
        task_id: Database task ID for tracking
        keywords: List of keywords to search for
        region_filter: Filter by specific region
        prefecture_filter: Filter by specific prefecture
        output_file: Optional output file path
        output_format: Output format ('json' or 'pretty')
    
    Returns:
        dict: Results of the scraping operation
    """
    # Default animal keywords if none provided
    if keywords is None:
        keywords = [
            "bovin",
            "porcin", 
            "volaille",
            "poules",
            "pondeuses",
            "poulets"
        ]
    
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
    
    logger.info(f"Starting enhanced Celery task for scraping with {len(keywords)} keywords")
    
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
    
    all_results = []
    results_by_keyword = {}
    results_by_prefecture = {}
    total_operations = len(prefectures_to_scrape) * len(keywords)
    current_operation = 0
    
    # Update total operations in database
    db_task.total_operations = total_operations
    db_task.save()
    
    try:
        for keyword in keywords:
            logger.info(f"Processing keyword: {keyword}")
            
            keyword_results = []
            keyword_prefecture_results = {}
            
            for prefecture in prefectures_to_scrape:
                current_operation += 1
                progress = f"[{current_operation}/{total_operations}]"
                
                logger.info(f"{progress} Scraping {prefecture['name']} ({prefecture['region']}) - {prefecture['domain']}")
                logger.info(f"Keyword: {keyword}")
                
                try:
                    # Check if task has been revoked (simplified check)
                    # Note: is_aborted() method may not be available in all Celery versions
                    # We'll skip this check for now to avoid errors
                    
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
                        
                        # Save individual result to database
                        ScrapingTaskResult.objects.update_or_create(
                            task=db_task,
                            prefecture_name=prefecture['name'],
                            keyword=keyword,
                            defaults={
                                'region_name': prefecture['region'],
                                'items_found': len(results)
                            }
                        )
                    else:
                        logger.warning(f"No results found for {prefecture['name']} with keyword '{keyword}'")
                        keyword_prefecture_results[prefecture['name']] = {
                            'prefecture': prefecture,
                            'results': [],
                            'count': 0
                        }
                        
                        # Save zero result to database
                        ScrapingTaskResult.objects.update_or_create(
                            task=db_task,
                            prefecture_name=prefecture['name'],
                            keyword=keyword,
                            defaults={
                                'region_name': prefecture['region'],
                                'items_found': 0
                            }
                        )
                        
                except Exception as e:
                    logger.error(f"Error scraping {prefecture['name']}: {e}")
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
        
        # Prepare final results
        final_results = {
            'summary': {
                'total_prefectures': len(prefectures_to_scrape),
                'total_keywords': len(keywords),
                'total_operations': total_operations,
                'total_items': len(all_results),
                'keywords': keywords
            },
            'results_by_keyword': results_by_keyword,
            'all_results': all_results
        }
        
        # Save results to file if specified
        if output_file:
            if output_format == 'json':
                output_data = json.dumps(final_results, indent=2, ensure_ascii=False)
            else:
                # Pretty format
                output_data = _format_results_pretty(results_by_keyword, keywords)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(output_data)
            logger.info(f"Results saved to {output_file}")
        
        # Mark task as completed in database
        db_task.mark_completed(
            results_summary=final_results['summary'],
            total_items=len(all_results)
        )
        
        logger.info(f"Enhanced task completed successfully. Found {len(all_results)} total items.")
        
        return {
            'status': 'SUCCESS',
            'message': f'Scraping completed successfully. Found {len(all_results)} items.',
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
