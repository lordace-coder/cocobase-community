from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from . import config as settings

# Database URL from environment
SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

# Create engine with minimal pool for Supabase Session mode
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_size=3,              # Only 3 persistent connections
    max_overflow=2,           # Max 2 additional = 5 total max
    pool_pre_ping=True,       # Check connections are alive
    pool_recycle=300,         # Recycle after 5 minutes
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
