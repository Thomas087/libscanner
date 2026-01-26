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
    redis_url = getattr(settings, 'REDIS_URL', os.environ.get('REDISCLOUD_URL') or os.environ.get('REDIS_URL'))
    
    if not redis_url:
        # Fallback for local development
        redis_url = 'redis://localhost:6379/0'
    
    try:
        # Parse the URL using urllib.parse (Python 3 equivalent of urlparse)
        parsed_url = urllib.parse.urlparse(redis_url)
        
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
