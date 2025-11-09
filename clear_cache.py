#!/usr/bin/env python3
"""
Clear FastAPI cache to resolve PickleType deserialization errors.

This script clears the in-memory cache that may contain stale data
with old PickleType format.
"""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv()


async def clear_fastapi_cache():
    """Clear FastAPI in-memory cache"""
    print("=" * 70)
    print("CLEARING FASTAPI CACHE")
    print("=" * 70)

    try:
        from fastapi_cache import FastAPICache
        from fastapi_cache.backends.inmemory import InMemoryBackend

        # Initialize/reinitialize cache with fresh backend
        FastAPICache.init(InMemoryBackend(), prefix="fastapi-cache")

        # Clear all cached data
        if FastAPICache._backend:
            await FastAPICache._backend.clear()
            print("✅ FastAPI in-memory cache cleared successfully")
        else:
            print("⚠️  No active cache backend found")

    except Exception as e:
        print(f"❌ Error clearing FastAPI cache: {e}")
        import traceback
        traceback.print_exc()


async def clear_redis_cache():
    """Clear Redis cache if configured"""
    print("\n" + "=" * 70)
    print("CLEARING REDIS CACHE")
    print("=" * 70)

    try:
        REDIS_URL = os.getenv("REDIS_URL")

        if not REDIS_URL or REDIS_URL == "redis://localhost:6379":
            print("⚠️  Redis not configured or using default - skipping")
            return

        import redis.asyncio as redis

        r = redis.from_url(REDIS_URL, decode_responses=True)

        # Test connection
        await r.ping()
        print(f"✅ Connected to Redis at {REDIS_URL}")

        # Get all keys with cache prefix
        keys = await r.keys("fastapi-cache:*")

        if keys:
            print(f"Found {len(keys)} cached keys")

            # Delete all cache keys
            deleted = await r.delete(*keys)
            print(f"✅ Deleted {deleted} cache entries from Redis")
        else:
            print("ℹ️  No cache keys found in Redis")

        await r.close()

    except ImportError:
        print("⚠️  redis package not installed - skipping Redis cache clear")
    except Exception as e:
        print(f"❌ Error clearing Redis cache: {e}")
        import traceback
        traceback.print_exc()


async def restart_sqlalchemy_sessions():
    """Force SQLAlchemy to refresh its metadata and session state"""
    print("\n" + "=" * 70)
    print("REFRESHING SQLALCHEMY METADATA")
    print("=" * 70)

    try:
        from app.core.database import engine, Base
        from sqlalchemy import inspect

        # Clear cached table metadata
        Base.metadata.clear()

        # Force reload metadata from database
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"✅ Found {len(tables)} tables in database")

        # Reflect the metadata from the database
        Base.metadata.reflect(bind=engine)
        print(f"✅ Reflected {len(Base.metadata.tables)} tables into metadata")

        # Verify the problematic columns
        print("\nVerifying column types:")
        if 'projects' in Base.metadata.tables:
            projects_table = Base.metadata.tables['projects']
            if 'allowed_origins' in projects_table.c:
                col_type = projects_table.c.allowed_origins.type
                print(f"  projects.allowed_origins: {type(col_type).__name__}")

        if 'app_users' in Base.metadata.tables:
            users_table = Base.metadata.tables['app_users']
            if 'roles' in users_table.c:
                col_type = users_table.c.roles.type
                print(f"  app_users.roles: {type(col_type).__name__}")

        print("✅ SQLAlchemy metadata refreshed")

        # Close all connections in the pool
        engine.dispose()
        print("✅ SQLAlchemy connection pool disposed")

    except Exception as e:
        print(f"❌ Error refreshing SQLAlchemy: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Main function to clear all caches"""
    print("\n🧹 CACHE CLEARING UTILITY")
    print("This will clear all application caches to resolve PickleType errors\n")

    await clear_fastapi_cache()
    await clear_redis_cache()
    await restart_sqlalchemy_sessions()

    print("\n" + "=" * 70)
    print("✨ CACHE CLEARING COMPLETE")
    print("=" * 70)
    print("\nNext steps:")
    print("1. Restart your application:")
    print("   docker-compose restart <service-name>")
    print("\n2. Or if running directly:")
    print("   pkill -f 'uvicorn'  # Stop the server")
    print("   # Then start it again")
    print("\n3. Verify the error is resolved by making a request")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
