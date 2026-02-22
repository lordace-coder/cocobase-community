import os
import redis.asyncio as redis
from dotenv import load_dotenv

load_dotenv()

# Get Redis URL from environment
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Async Redis instance for general use (with decode_responses=True)
instance = None


async def init_redis():
    """Initialize the async Redis connection"""
    global instance
    instance = redis.from_url(
        REDIS_URL, decode_responses=True, encoding="utf-8"  # For normal operations
    )
    # Test the connection
    await instance.ping()
    return instance


async def close_redis():
    """Close the Redis connection"""
    global instance
    if instance:
        await instance.close()
        instance = None


def get_redis_url():
    """Get the Redis URL for creating new connections"""
    return REDIS_URL


async def get_pubsub_redis():
    """
    Create a new Redis connection for pubsub operations.
    PubSub requires decode_responses=False
    """
    return redis.from_url(
        REDIS_URL, decode_responses=False, encoding="utf-8"  # Required for pubsub
    )


def get_redis_instance():
    """Get the current Redis instance"""
    if instance is None:
        raise RuntimeError("Redis not initialized. Call init_redis() first.")
    return instance
