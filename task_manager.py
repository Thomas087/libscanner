#!/usr/bin/env python
"""
Task management utility for Celery tasks.
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

from celery import current_app


class TaskManager:
    """Utility class to manage Celery tasks."""
    
    def __init__(self):
        self.app = current_app
    
    def list_active_tasks(self):
        """List all currently active tasks."""
        inspect = self.app.control.inspect()
        active_tasks = inspect.active()
        
        # Also check Redis for tasks in PROGRESS state
        redis_tasks = self._get_redis_tasks()
        
        tasks = []
        if active_tasks:
            for worker, worker_tasks in active_tasks.items():
                for task in worker_tasks:
                    task_info = {
                        'worker': worker,
                        'id': task.get('id'),
                        'name': task.get('name'),
                        'args': task.get('args', []),
                        'kwargs': task.get('kwargs', {}),
                        'time_start': task.get('time_start'),
                        'source': 'inspect'
                    }
                    tasks.append(task_info)
        
        # Add Redis tasks
        tasks.extend(redis_tasks)
        
        if not tasks:
            print("No active tasks found")
            return []
                
        return tasks
    
    def _get_redis_tasks(self):
        """Get tasks from Redis that are in PROGRESS state."""
        import redis
        from django.conf import settings
        
        tasks = []
        try:
            # Connect to Redis
            redis_url = settings.CELERY_RESULT_BACKEND
            r = redis.from_url(redis_url)
            
            # Get all task metadata keys
            task_keys = r.keys('celery-task-meta-*')
            
            for key in task_keys:
                task_data = r.get(key)
                if task_data:
                    import json
                    try:
                        data = json.loads(task_data)
                        task_id = data.get('task_id')
                        status = data.get('status')
                        result = data.get('result', {})
                        
                        if status == 'PROGRESS':
                            task_info = {
                                'worker': 'redis',
                                'id': task_id,
                                'name': 'scrape_animal_keywords_task',
                                'args': [],
                                'kwargs': {},
                                'time_start': None,
                                'source': 'redis',
                                'status': status,
                                'progress': result
                            }
                            tasks.append(task_info)
                            
                    except json.JSONDecodeError:
                        continue
                        
        except Exception as e:
            print(f"Error checking Redis tasks: {e}")
            
        return tasks
    
    def revoke_task(self, task_id, terminate=True):
        """Revoke a specific task."""
        try:
            # Try multiple revocation methods
            self.app.control.revoke(task_id, terminate=terminate)
            
            # Also try to revoke from Redis directly
            import redis
            from django.conf import settings
            
            redis_url = settings.CELERY_RESULT_BACKEND
            r = redis.from_url(redis_url)
            
            # Remove the task metadata from Redis
            r.delete(f'celery-task-meta-{task_id}')
            
            print(f"Task {task_id} has been revoked")
            return True
        except Exception as e:
            print(f"Failed to revoke task {task_id}: {e}")
            return False
    
    def revoke_all_tasks(self):
        """Revoke all active tasks."""
        active_tasks = self.list_active_tasks()
        revoked_count = 0
        
        for task in active_tasks:
            if self.revoke_task(task['id']):
                revoked_count += 1
                
        print(f"Revoked {revoked_count} tasks")
        return revoked_count
    
    def purge_queue(self):
        """Purge all tasks from the queue."""
        try:
            self.app.control.purge()
            print("All tasks have been purged from the queue")
            return True
        except Exception as e:
            print(f"Failed to purge queue: {e}")
            return False
    
    def force_stop_workers(self):
        """Force stop all Celery workers."""
        import subprocess
        import signal
        import os
        
        try:
            # Find and kill Celery worker processes
            result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
            lines = result.stdout.split('\n')
            
            celery_pids = []
            for line in lines:
                if 'celery' in line and 'worker' in line and 'grep' not in line:
                    parts = line.split()
                    if len(parts) > 1:
                        pid = parts[1]
                        celery_pids.append(pid)
            
            if celery_pids:
                print(f"Found {len(celery_pids)} Celery worker processes")
                for pid in celery_pids:
                    try:
                        os.kill(int(pid), signal.SIGTERM)
                        print(f"Sent SIGTERM to worker PID {pid}")
                    except Exception as e:
                        print(f"Failed to kill PID {pid}: {e}")
                
                # Wait a moment and then force kill if needed
                import time
                time.sleep(2)
                
                for pid in celery_pids:
                    try:
                        os.kill(int(pid), signal.SIGKILL)
                        print(f"Force killed worker PID {pid}")
                    except:
                        pass  # Process might already be dead
                        
                print("All Celery workers have been stopped")
                return True
            else:
                print("No Celery worker processes found")
                return False
                
        except Exception as e:
            print(f"Failed to stop workers: {e}")
            return False
    
    def get_task_status(self, task_id):
        """Get the status of a specific task."""
        try:
            result = self.app.AsyncResult(task_id)
            return {
                'id': task_id,
                'status': result.status,
                'result': result.result,
                'info': result.info
            }
        except Exception as e:
            print(f"Failed to get task status: {e}")
            return None
    
    def show_worker_stats(self):
        """Show statistics about workers."""
        inspect = self.app.control.inspect()
        stats = inspect.stats()
        
        if not stats:
            print("No workers found")
            return
            
        print("Worker Statistics:")
        print("=" * 50)
        for worker, stat in stats.items():
            print(f"Worker: {worker}")
            print(f"  Pool: {stat.get('pool', {}).get('max-concurrency', 'Unknown')}")
            print(f"  Total tasks: {stat.get('total', 'Unknown')}")
            print(f"  Active tasks: {stat.get('active', 'Unknown')}")
            print("-" * 30)


def main():
    """Main function for command-line usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Manage Celery tasks')
    parser.add_argument('action', choices=['list', 'revoke', 'revoke-all', 'purge', 'status', 'stats', 'force-stop'],
                       help='Action to perform')
    parser.add_argument('--task-id', help='Task ID for revoke/status actions')
    
    args = parser.parse_args()
    
    manager = TaskManager()
    
    if args.action == 'list':
        tasks = manager.list_active_tasks()
        if tasks:
            print(f"Found {len(tasks)} active tasks:")
            for task in tasks:
                print(f"  {task['id']} - {task['name']} on {task['worker']} (source: {task.get('source', 'unknown')})")
                if task.get('status') == 'PROGRESS' and task.get('progress'):
                    progress = task['progress']
                    current = progress.get('current', 0)
                    total = progress.get('total', 0)
                    prefecture = progress.get('prefecture', 'Unknown')
                    keyword = progress.get('keyword', 'Unknown')
                    print(f"    Progress: {current}/{total} - {prefecture} ({keyword})")
        else:
            print("No active tasks")
            
    elif args.action == 'revoke':
        if not args.task_id:
            print("Error: --task-id is required for revoke action")
            return
        manager.revoke_task(args.task_id)
        
    elif args.action == 'revoke-all':
        manager.revoke_all_tasks()
        
    elif args.action == 'purge':
        manager.purge_queue()
        
    elif args.action == 'status':
        if not args.task_id:
            print("Error: --task-id is required for status action")
            return
        status = manager.get_task_status(args.task_id)
        if status:
            print(f"Task {status['id']}: {status['status']}")
            if status['result']:
                print(f"Result: {status['result']}")
                
    elif args.action == 'stats':
        manager.show_worker_stats()
        
    elif args.action == 'force-stop':
        manager.force_stop_workers()


if __name__ == '__main__':
    main()
