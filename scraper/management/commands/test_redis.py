"""
Django management command to test Redis connection.
"""
import os
import redis
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Test Redis connection and Celery configuration'

    def handle(self, *args, **options):
        self.stdout.write("Testing Redis connection...")
        
        # Get Redis URL
        redis_url = getattr(settings, 'REDIS_URL', os.environ.get('REDIS_URL', 'redis://localhost:6379/0'))
        self.stdout.write(f"Redis URL: {redis_url}")
        
        try:
            # Test Redis connection using proper Heroku method
            from libscanner.redis_connection import get_redis_connection, test_redis_connection
            
            # Test connection
            success, message = test_redis_connection()
            if success:
                self.stdout.write(self.style.SUCCESS("✓ Redis connection successful"))
                self.stdout.write(f"  {message}")
            else:
                self.stdout.write(self.style.ERROR(f"✗ Redis connection failed: {message}"))
                return False
            
            # Get Redis info
            r = get_redis_connection()
            info = r.info()
            self.stdout.write(f"  Redis version: {info.get('redis_version', 'Unknown')}")
            self.stdout.write(f"  Memory used: {info.get('used_memory_human', 'Unknown')}")
            self.stdout.write(f"  Connected clients: {info.get('connected_clients', 'Unknown')}")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ Redis connection failed: {e}"))
            return
        
        # Test Celery configuration
        self.stdout.write("\nTesting Celery configuration...")
        
        try:
            from celery import current_app
            self.stdout.write(f"Celery broker URL: {current_app.conf.broker_url}")
            self.stdout.write(f"Celery result backend: {current_app.conf.result_backend}")
            
            # Test Celery connection
            inspect = current_app.control.inspect()
            stats = inspect.stats()
            if stats:
                self.stdout.write(self.style.SUCCESS("✓ Celery connection successful"))
                self.stdout.write(f"Active workers: {len(stats)}")
            else:
                self.stdout.write(self.style.WARNING("⚠ No active Celery workers found"))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ Celery connection failed: {e}"))
        
        # Test task creation
        self.stdout.write("\nTesting task creation...")
        try:
            from scraper.tasks import scrape_animal_keywords_enhanced_task
            self.stdout.write(self.style.SUCCESS("✓ Task import successful"))
            
            # Test task creation (don't actually run it)
            task = scrape_animal_keywords_enhanced_task.s()
            self.stdout.write(self.style.SUCCESS("✓ Task creation successful"))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ Task creation failed: {e}"))
        
        self.stdout.write("\n" + "="*50)
        self.stdout.write("Redis and Celery configuration test complete!")
