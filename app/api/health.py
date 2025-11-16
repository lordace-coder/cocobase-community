"""
Health check and monitoring endpoints.

Provides detailed health status for database connections, Redis, and system resources.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db, engine
from app.services.redis_worker import get_redis_instance
from datetime import datetime
import logging
import psutil
import os

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/health", tags=["Health & Monitoring"])


@router.get("/")
async def health_check():
    """
    Basic health check - returns 200 if service is alive.
    Use this for load balancer health checks.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "CocoBase API"
    }


@router.get("/database")
async def database_health(db: Session = Depends(get_db)):
    """
    Detailed database health check with connection pool statistics.

    Shows:
    - Connection pool status
    - Active/idle connections
    - Database connectivity
    - Query performance
    """
    try:
        # Test database connectivity with a simple query
        start_time = datetime.utcnow()
        result = db.execute(text("SELECT 1"))
        query_time = (datetime.utcnow() - start_time).total_seconds() * 1000  # ms

        # Get connection pool statistics
        pool = engine.pool
        pool_status = {
            "pool_size": pool.size(),
            "connections_in_pool": pool.checkedin(),
            "connections_checked_out": pool.checkedout(),
            "overflow_connections": pool.overflow(),
            "total_connections": pool.checkedout() + pool.checkedin(),
        }

        # Calculate health metrics
        total_capacity = engine.pool._pool.maxsize + engine.pool._max_overflow
        usage_percentage = (pool_status["connections_checked_out"] / total_capacity) * 100

        # Determine status
        if usage_percentage >= 90:
            status = "critical"
            message = "Connection pool nearly exhausted"
        elif usage_percentage >= 70:
            status = "warning"
            message = "High connection pool usage"
        else:
            status = "healthy"
            message = "Connection pool operating normally"

        return {
            "status": status,
            "message": message,
            "database": {
                "connected": True,
                "query_response_time_ms": round(query_time, 2),
            },
            "connection_pool": {
                **pool_status,
                "max_capacity": total_capacity,
                "usage_percentage": round(usage_percentage, 2),
                "available_connections": total_capacity - pool_status["connections_checked_out"],
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Database health check failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.get("/redis")
async def redis_health():
    """
    Redis connection health check.

    Shows:
    - Redis connectivity
    - Response time
    - Memory usage (if available)
    """
    try:
        redis = await get_redis_instance()

        # Test Redis connectivity
        start_time = datetime.utcnow()
        await redis.ping()
        response_time = (datetime.utcnow() - start_time).total_seconds() * 1000  # ms

        # Get Redis info (optional)
        try:
            info = await redis.info()
            memory_used = info.get('used_memory_human', 'N/A')
            connected_clients = info.get('connected_clients', 'N/A')
        except:
            memory_used = 'N/A'
            connected_clients = 'N/A'

        return {
            "status": "healthy",
            "message": "Redis connected",
            "redis": {
                "connected": True,
                "response_time_ms": round(response_time, 2),
                "memory_used": memory_used,
                "connected_clients": connected_clients,
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Redis health check failed: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "message": str(e),
            "redis": {
                "connected": False
            },
            "timestamp": datetime.utcnow().isoformat()
        }


@router.get("/system")
async def system_health():
    """
    System resource health check.

    Shows:
    - CPU usage
    - Memory usage
    - Disk usage
    - Process information
    """
    try:
        # CPU information
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()

        # Memory information
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_used_gb = memory.used / (1024 ** 3)
        memory_total_gb = memory.total / (1024 ** 3)

        # Disk information
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent
        disk_used_gb = disk.used / (1024 ** 3)
        disk_total_gb = disk.total / (1024 ** 3)

        # Process information
        process = psutil.Process(os.getpid())
        process_memory_mb = process.memory_info().rss / (1024 ** 2)
        process_threads = process.num_threads()

        # Determine status
        if cpu_percent >= 90 or memory_percent >= 90 or disk_percent >= 90:
            status = "critical"
            message = "System resources critically high"
        elif cpu_percent >= 70 or memory_percent >= 70 or disk_percent >= 80:
            status = "warning"
            message = "System resources elevated"
        else:
            status = "healthy"
            message = "System resources normal"

        return {
            "status": status,
            "message": message,
            "cpu": {
                "usage_percent": round(cpu_percent, 2),
                "cores": cpu_count,
            },
            "memory": {
                "usage_percent": round(memory_percent, 2),
                "used_gb": round(memory_used_gb, 2),
                "total_gb": round(memory_total_gb, 2),
                "available_gb": round(memory.available / (1024 ** 3), 2),
            },
            "disk": {
                "usage_percent": round(disk_percent, 2),
                "used_gb": round(disk_used_gb, 2),
                "total_gb": round(disk_total_gb, 2),
                "available_gb": round(disk.free / (1024 ** 3), 2),
            },
            "process": {
                "memory_mb": round(process_memory_mb, 2),
                "threads": process_threads,
                "pid": os.getpid(),
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"System health check failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.get("/full")
async def full_health_check(db: Session = Depends(get_db)):
    """
    Comprehensive health check combining all health endpoints.

    Use this for detailed monitoring and debugging.
    Returns combined status of database, Redis, and system resources.
    """
    try:
        # Run all health checks
        db_health = await database_health(db)
        redis_health_result = await redis_health()
        system_health_result = await system_health()

        # Determine overall status
        statuses = [
            db_health.get("status"),
            redis_health_result.get("status"),
            system_health_result.get("status")
        ]

        if "critical" in statuses or "unhealthy" in statuses:
            overall_status = "unhealthy"
        elif "warning" in statuses:
            overall_status = "degraded"
        else:
            overall_status = "healthy"

        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {
                "database": db_health,
                "redis": redis_health_result,
                "system": system_health_result,
            }
        }

    except Exception as e:
        logger.error(f"Full health check failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=503,
            detail={
                "status": "error",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.get("/scheduler")
async def scheduler_health():
    """
    Background scheduler health check.

    Shows:
    - Scheduler status
    - Scheduled jobs
    - Next run times
    """
    try:
        from app.core.scheduler import get_scheduler_status

        status_info = get_scheduler_status()

        return {
            "status": "healthy" if status_info["running"] else "stopped",
            "scheduler": status_info,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Scheduler health check failed: {e}", exc_info=True)
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
