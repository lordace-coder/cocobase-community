from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool, NullPool
from sqlalchemy.exc import DBAPIError, OperationalError
from . import config as settings
from sqlalchemy.engine import Engine
import time
import logging

logger = logging.getLogger(__name__)


def create_engine_with_retries(url, max_retries=3, **kwargs):
    """Create SQLAlchemy engine with retry logic and optimized settings."""
    
    for attempt in range(max_retries):
        try:
            # Determine if this is SQLite or PostgreSQL
            is_sqlite = url.startswith("sqlite")
            
            # Base configuration
            engine_config = {
                "pool_pre_ping": True,
                "echo": False,  # Set to True for debugging SQL queries
                "future": True,  # Use SQLAlchemy 2.0 style
            }
            
            if is_sqlite:
                # SQLite-specific configuration
                engine_config.update({
                    "connect_args": {
                        "check_same_thread": False,
                        "timeout": 10,
                    },
                    "poolclass": NullPool,  # No pooling for SQLite
                })
            else:
                # PostgreSQL/Supabase configuration
                engine_config.update({
                    "pool_size": 10,
                    "max_overflow": 20,
                    "pool_timeout": 30,
                    "pool_recycle": 1800,  # 30 minutes
                    "connect_args": {
                        "connect_timeout": 10,
                    },
                })
            
            # Merge with any additional kwargs
            engine_config.update(kwargs)
            
            engine = create_engine(url, **engine_config)
            
            # Test the connection
            with engine.connect() as conn:
                # For PostgreSQL, verify version and compatibility
                if not is_sqlite:
                    from sqlalchemy import text
                    result = conn.execute(text("SELECT version()"))
                    version_info = result.scalar()
                    logger.info(f"Connected to database: {version_info}")
                    
                    # Verify pg_index has indnullsnotdistinct (should be in PG 15+)
                    result = conn.execute(text("""
                        SELECT EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_schema = 'pg_catalog'
                            AND table_name = 'pg_index' 
                            AND column_name = 'indnullsnotdistinct'
                        )
                    """))
                    has_column = result.scalar()
                    if not has_column:
                        logger.warning("Database missing 'indnullsnotdistinct' column - may cause reflection issues")
                
                logger.info(f"Database connection established (attempt {attempt + 1})")
            
            return engine
            
        except (DBAPIError, OperationalError) as e:
            logger.error(f"Database connection attempt {attempt + 1} failed: {e}")
            if attempt == max_retries - 1:
                raise
            # Exponential backoff
            time.sleep(2 ** attempt)


# Create engine
SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL
engine = create_engine_with_retries(SQLALCHEMY_DATABASE_URL)

# Session configuration
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,  # Don't expire objects after commit
)

Base = declarative_base()


# Add connection event listeners for better error handling
@event.listens_for(Engine, "connect")
def receive_connect(dbapi_conn, connection_record):
    """Event listener for new database connections."""
    logger.debug("New database connection established")


@event.listens_for(Engine, "checkout")
def receive_checkout(dbapi_conn, connection_record, connection_proxy):
    """Event listener for connection checkout from pool."""
    logger.debug("Connection checked out from pool")


@event.listens_for(Engine, "checkin")
def receive_checkin(dbapi_conn, connection_record):
    """Event listener for connection checkin to pool."""
    logger.debug("Connection returned to pool")


def get_db():
    """
    Dependency function for FastAPI to get database sessions.
    Includes error handling and automatic rollback.
    """
    db = SessionLocal()
    try:
        yield db
    except DBAPIError as e:
        logger.error(f"Database error occurred: {e}")
        db.rollback()
        raise
    except Exception as e:
        logger.error(f"Unexpected error in database session: {e}")
        db.rollback()
        raise
    finally:
        db.close()


# Health check function
def check_database_health():
    """Check if database connection is healthy."""
    try:
        with engine.connect() as conn:
            from sqlalchemy import text
            conn.execute(text("SELECT 1"))
            return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


# Optional: Create a separate engine for async operations if needed
def create_async_engine_with_retries(url, max_retries=3):
    """Create async SQLAlchemy engine for async operations."""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker as async_sessionmaker
    
    # Convert sync URL to async URL
    async_url = url.replace("postgresql://", "postgresql+asyncpg://")
    
    for attempt in range(max_retries):
        try:
            async_engine = create_async_engine(
                async_url,
                pool_pre_ping=True,
                pool_size=10,
                max_overflow=20,
                pool_timeout=30,
                pool_recycle=3600,
                echo=False,
            )
            
            logger.info(f"Async database engine created (attempt {attempt + 1})")
            return async_engine
            
        except Exception as e:
            logger.error(f"Async engine creation attempt {attempt + 1} failed: {e}")
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)