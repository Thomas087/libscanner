"""
Redis connection utilities using the proper Heroku Redis connection method.
Based on the official Redis documentation for Heroku.
"""
import os
import urllib.parse
import redis
from django.conf import settings


def get_redis_connection():
    """
    Create a Redis connection using the proper Heroku Redis URL parsing.
    Based on: https://devcenter.heroku.com/articles/heroku-redis#connecting-in-python
    """
    # Get Redis URL from Django settings (which handles Heroku URL parsing)
    from django.conf import settings
    redis_url = getattr(settings, 'REDIS_URL', os.environ.get('REDIS_URL'))
    
    if not redis_url:
        # Fallback for local development
        redis_url = 'redis://localhost:6379/0'
    
    try:
        # Parse the URL using urllib.parse (Python 3 equivalent of urlparse)
        parsed_url = urllib.parse.urlparse(redis_url)
        
        # Debug information
        print(f"DEBUG: Redis URL: {redis_url}")
        print(f"DEBUG: Parsed hostname: {parsed_url.hostname}")
        print(f"DEBUG: Parsed port: {parsed_url.port}")
        print(f"DEBUG: Has password: {bool(parsed_url.password)}")
        
        # Create Redis connection with parsed components
        # This is the exact method from the Heroku documentation
        r = redis.Redis(
            host=parsed_url.hostname,
            port=parsed_url.port,
            password=parsed_url.password,
            decode_responses=True,  # Automatically decode responses to strings
            socket_connect_timeout=30,
            socket_timeout=30,
            retry_on_timeout=True,
            health_check_interval=30
        )
        
        # Test the connection
        r.ping()
        return r
        
    except Exception as e:
        # Fallback to simple URL connection if parsing fails
        try:
            r = redis.from_url(redis_url)
            r.ping()
            return r
        except Exception as fallback_error:
            raise Exception(f"Redis connection failed: {e}. Fallback also failed: {fallback_error}")


def test_redis_connection():
    """
    Test Redis connection and return status information.
    """
    try:
        r = get_redis_connection()
        
        # Test basic operations
        r.set('test_key', 'test_value', ex=60)  # Set with 60 second expiration
        value = r.get('test_key')
        r.delete('test_key')
        
        if value == 'test_value':
            return True, "Redis connection successful"
        else:
            return False, "Redis set/get test failed"
            
    except Exception as e:
        return False, f"Redis connection failed: {e}"


def get_redis_info():
    """
    Get Redis connection information for debugging.
    """
    try:
        r = get_redis_connection()
        info = r.info()
        return {
            'connected': True,
            'redis_version': info.get('redis_version'),
            'used_memory': info.get('used_memory_human'),
            'connected_clients': info.get('connected_clients'),
            'uptime': info.get('uptime_in_seconds')
        }
    except Exception as e:
        return {
            'connected': False,
            'error': str(e)
        }
