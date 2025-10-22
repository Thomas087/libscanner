"""
Django management command to manage Celery tasks.
"""
import json
from django.core.management.base import BaseCommand, CommandError
from celery import current_app


class Command(BaseCommand):
    help = 'Manage Celery tasks (list, revoke, inspect)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--action',
            type=str,
            choices=['list', 'revoke', 'purge', 'inspect'],
            required=True,
            help='Action to perform: list, revoke, purge, or inspect'
        )
        parser.add_argument(
            '--task-id',
            type=str,
            help='Task ID for revoke action'
        )
        parser.add_argument(
            '--worker',
            type=str,
            help='Worker name for inspect action'
        )

    def handle(self, *args, **options):
        action = options['action']
        
        try:
            if action == 'list':
                self._list_active_tasks()
            elif action == 'revoke':
                task_id = options.get('task_id')
                if not task_id:
                    raise CommandError('--task-id is required for revoke action')
                self._revoke_task(task_id)
            elif action == 'purge':
                self._purge_tasks()
            elif action == 'inspect':
                self._inspect_workers()
                
        except Exception as e:
            raise CommandError(f'Error performing action {action}: {e}')

    def _list_active_tasks(self):
        """List all active tasks."""
        self.stdout.write("Fetching active tasks...")
        
        inspect = current_app.control.inspect()
        active_tasks = inspect.active()
        
        # Also check for tasks in PROGRESS state from Redis
        self._check_progress_tasks()
        
        if not active_tasks:
            self.stdout.write(self.style.WARNING("No active tasks found via inspect"))
            return
            
        for worker, tasks in active_tasks.items():
            self.stdout.write(f"\nWorker: {worker}")
            self.stdout.write("-" * 50)
            
            for task in tasks:
                task_id = task.get('id', 'Unknown')
                task_name = task.get('name', 'Unknown')
                args = task.get('args', [])
                kwargs = task.get('kwargs', {})
                
                self.stdout.write(f"Task ID: {task_id}")
                self.stdout.write(f"Name: {task_name}")
                self.stdout.write(f"Args: {args}")
                self.stdout.write(f"Kwargs: {kwargs}")
                self.stdout.write("-" * 30)
    
    def _check_progress_tasks(self):
        """Check for tasks in PROGRESS state from Redis."""
        import redis
        from django.conf import settings
        
        try:
            # Connect to Redis
            redis_url = settings.CELERY_RESULT_BACKEND
            r = redis.from_url(redis_url)
            
            # Get all task metadata keys
            task_keys = r.keys('celery-task-meta-*')
            
            if task_keys:
                self.stdout.write(f"\nFound {len(task_keys)} task(s) in Redis:")
                self.stdout.write("=" * 50)
                
                for key in task_keys:
                    task_data = r.get(key)
                    if task_data:
                        import json
                        try:
                            data = json.loads(task_data)
                            task_id = data.get('task_id', 'Unknown')
                            status = data.get('status', 'Unknown')
                            result = data.get('result', {})
                            
                            self.stdout.write(f"Task ID: {task_id}")
                            self.stdout.write(f"Status: {status}")
                            
                            if status == 'PROGRESS' and isinstance(result, dict):
                                current = result.get('current', 0)
                                total = result.get('total', 0)
                                prefecture = result.get('prefecture', 'Unknown')
                                keyword = result.get('keyword', 'Unknown')
                                
                                self.stdout.write(f"Progress: {current}/{total}")
                                self.stdout.write(f"Current: {prefecture} - {keyword}")
                            
                            self.stdout.write("-" * 30)
                            
                        except json.JSONDecodeError:
                            self.stdout.write(f"Could not parse task data for {key}")
                            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error checking Redis tasks: {e}"))

    def _revoke_task(self, task_id):
        """Revoke a specific task."""
        self.stdout.write(f"Revoking task: {task_id}")
        
        try:
            # Revoke the task
            current_app.control.revoke(task_id, terminate=True)
            self.stdout.write(self.style.SUCCESS(f"Task {task_id} has been revoked"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to revoke task {task_id}: {e}"))

    def _purge_tasks(self):
        """Purge all tasks from the queue."""
        self.stdout.write("Purging all tasks from the queue...")
        
        try:
            # Purge all tasks
            current_app.control.purge()
            self.stdout.write(self.style.SUCCESS("All tasks have been purged"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to purge tasks: {e}"))

    def _inspect_workers(self):
        """Inspect worker status."""
        self.stdout.write("Inspecting workers...")
        
        inspect = current_app.control.inspect()
        
        # Get worker stats
        stats = inspect.stats()
        if stats:
            self.stdout.write("\nWorker Statistics:")
            self.stdout.write("=" * 50)
            for worker, stat in stats.items():
                self.stdout.write(f"Worker: {worker}")
                self.stdout.write(f"  Pool: {stat.get('pool', {}).get('max-concurrency', 'Unknown')}")
                self.stdout.write(f"  Total tasks: {stat.get('total', 'Unknown')}")
                self.stdout.write(f"  Active tasks: {stat.get('active', 'Unknown')}")
                self.stdout.write("-" * 30)
        
        # Get registered tasks
        registered = inspect.registered()
        if registered:
            self.stdout.write("\nRegistered Tasks:")
            self.stdout.write("=" * 50)
            for worker, tasks in registered.items():
                self.stdout.write(f"Worker: {worker}")
                for task in tasks:
                    self.stdout.write(f"  - {task}")
                self.stdout.write("-" * 30)
