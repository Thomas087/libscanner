#!/usr/bin/env python
"""
Script to start Celery worker for the libscanner project.
"""
import os
import sys
import django
from django.conf import settings

# Add the project directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'libscanner.settings')
django.setup()

if __name__ == '__main__':
    from celery import current_app
    
    # Start the worker
    worker = current_app.Worker(
        concurrency=1,  # Single worker to avoid conflicts
        loglevel='INFO',
        hostname='libscanner-worker@%h'
    )
    worker.start()
