from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from . import config as settings

# Database URL from environment
SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

# Create engine optimized for Supabase with 2 Fly.io machines
# Total connections across 2 machines: up to 20 (10 per machine)
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_size=5,              # 5 persistent connections per machine
    max_overflow=5,           # Up to 5 additional = 10 max per machine
    pool_pre_ping=True,       # Check connections are alive before using
    pool_recycle=3600,        # Recycle connections after 1 hour (was 5 min)
    pool_timeout=30,          # Wait max 30 seconds for connection from pool
    echo_pool=False,          # Set to True to debug pool issues
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
