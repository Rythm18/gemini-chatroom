import redis
from typing import Optional, Union
from app.core.config import settings
import json
import logging

logger = logging.getLogger(__name__)

class RedisClient:
    """Redis client for caching and data storage"""
    
    def __init__(self):
        try:
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
            self.redis_client.ping()
            logger.info("Redis connection established successfully")
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            self.redis_client = None
    
    def is_connected(self) -> bool:
        """Check if Redis is connected"""
        if not self.redis_client:
            return False
        try:
            self.redis_client.ping()
            return True
        except:
            return False
    
    def set(self, key: str, value: Union[str, dict], expire_seconds: Optional[int] = None) -> bool:
        """
        Set a value in Redis
        
        Args:
            key: The key to store
            value: The value to store (string or dict)
            expire_seconds: Optional expiration time in seconds
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_connected():
            return False
            
        try:
            if isinstance(value, dict):
                value = json.dumps(value)
            
            result = self.redis_client.set(key, value, ex=expire_seconds)
            return result is not None
        except Exception as e:
            logger.error(f"Redis SET error: {e}")
            return False
    
    def get(self, key: str) -> Optional[str]:
        """
        Get a value from Redis
        
        Args:
            key: The key to retrieve
            
        Returns:
            str: The value if found, None otherwise
        """
        if not self.is_connected():
            return None
            
        try:
            return self.redis_client.get(key)
        except Exception as e:
            logger.error(f"Redis GET error: {e}")
            return None
    
    def get_json(self, key: str) -> Optional[dict]:
        """
        Get a JSON value from Redis
        
        Args:
            key: The key to retrieve
            
        Returns:
            dict: The parsed JSON value if found, None otherwise
        """
        value = self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return None
        return None
    
    def delete(self, key: str) -> bool:
        """
        Delete a key from Redis
        
        Args:
            key: The key to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_connected():
            return False
            
        try:
            result = self.redis_client.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"Redis DELETE error: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """
        Check if a key exists in Redis
        
        Args:
            key: The key to check
            
        Returns:
            bool: True if key exists, False otherwise
        """
        if not self.is_connected():
            return False
            
        try:
            return self.redis_client.exists(key) > 0
        except Exception as e:
            logger.error(f"Redis EXISTS error: {e}")
            return False

redis_client = RedisClient() 