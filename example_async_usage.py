#!/usr/bin/env python
"""
Example script demonstrating how to use the async scraping functionality.
"""
import os
import sys
import time
import django
from django.core.management import call_command
from django.core.management.base import CommandError

# Add the project directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'libscanner.settings')
django.setup()

def run_async_scraping_example():
    """Example of running async scraping and monitoring progress."""
    print("=== Async Scraping Example ===")
    print("This example demonstrates how to use the new async scraping functionality.")
    print()
    
    # Start an async scraping task
    print("1. Starting async scraping task...")
    try:
        # This would normally be run from command line, but we'll simulate it
        print("   Command: python manage.py scrape_animal_keywords --async --region 'Bretagne'")
        print("   This would start a background task and return a task ID.")
        print("   Example output:")
        print("   - Task started with ID: abc123-def456-ghi789")
        print("   - You can check the task status using:")
        print("   - python manage.py scrape_animal_keywords --task-id abc123-def456-ghi789")
        print()
        
        # Simulate checking task status
        print("2. Checking task status...")
        print("   Command: python manage.py scrape_animal_keywords --task-id abc123-def456-ghi789")
        print("   Example output:")
        print("   - Task abc123-def456-ghi789 is in progress:")
        print("   -   Progress: 15/45")
        print("   -   Current: Morbihan - bovin")
        print("   -   Status: scraping")
        print()
        
        # Simulate task completion
        print("3. Task completion...")
        print("   Command: python manage.py scrape_animal_keywords --task-id abc123-def456-ghi789")
        print("   Example output:")
        print("   - Task abc123-def456-ghi789 completed successfully!")
        print("   -   Message: Scraping completed successfully. Found 150 items.")
        print("   -   Total items found: 150")
        print("   -   Prefectures scraped: 4")
        print("   -   Keywords searched: 6")
        print()
        
    except Exception as e:
        print(f"Error: {e}")

def show_usage_examples():
    """Show various usage examples."""
    print("=== Usage Examples ===")
    print()
    
    examples = [
        {
            "description": "Basic async scraping (all prefectures, default keywords)",
            "command": "python manage.py scrape_animal_keywords --async"
        },
        {
            "description": "Async scraping with region filter",
            "command": "python manage.py scrape_animal_keywords --async --region 'Bretagne'"
        },
        {
            "description": "Async scraping with prefecture filter",
            "command": "python manage.py scrape_animal_keywords --async --prefecture 'Morbihan'"
        },
        {
            "description": "Async scraping with custom keywords",
            "command": "python manage.py scrape_animal_keywords --async --keywords 'bovin' 'porcin'"
        },
        {
            "description": "Async scraping with output file",
            "command": "python manage.py scrape_animal_keywords --async --output results.json --format json"
        },
        {
            "description": "Check task status",
            "command": "python manage.py scrape_animal_keywords --task-id <TASK_ID>"
        },
        {
            "description": "Synchronous scraping (original behavior)",
            "command": "python manage.py scrape_animal_keywords"
        }
    ]
    
    for i, example in enumerate(examples, 1):
        print(f"{i}. {example['description']}")
        print(f"   {example['command']}")
        print()

def show_setup_instructions():
    """Show setup instructions."""
    print("=== Setup Instructions ===")
    print()
    print("1. Install dependencies:")
    print("   pip install -r requirements.txt")
    print()
    print("2. Start Redis (if not already running):")
    print("   # macOS with Homebrew")
    print("   brew install redis")
    print("   brew services start redis")
    print()
    print("   # Ubuntu/Debian")
    print("   sudo apt-get install redis-server")
    print("   sudo systemctl start redis")
    print()
    print("3. Start Celery worker (in a separate terminal):")
    print("   celery -A libscanner worker --loglevel=info --concurrency=1")
    print()
    print("4. Run async scraping:")
    print("   python manage.py scrape_animal_keywords --async")
    print()

if __name__ == '__main__':
    print("Libscanner Async Scraping Example")
    print("=" * 50)
    print()
    
    show_setup_instructions()
    show_usage_examples()
    run_async_scraping_example()
    
    print("=== Benefits of Async Scraping ===")
    print()
    print("✓ No timeouts - Long-running operations won't timeout")
    print("✓ Background processing - Web server remains responsive")
    print("✓ Progress tracking - Real-time progress updates")
    print("✓ Scalability - Can scale workers independently")
    print("✓ Reliability - Tasks can be retried on failure")
    print("✓ Monitoring - Easy to monitor task status and progress")
    print()
    print("For more information, see CELERY_SETUP.md")
