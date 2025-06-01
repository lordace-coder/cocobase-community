from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import DBAPIError
from . import config as settings
from sqlalchemy.engine import Engine
import sqlite3
import time


def create_engine_with_retries(url, max_retries=3, **kwargs):
    for attempt in range(max_retries):
        try:
            engine = create_engine(
                url,
                pool_pre_ping=True,  # Enables connection health checks
                pool_size=5,  # Maximum number of connections to keep persistently
                max_overflow=10,  # Maximum number of connections to create when pool is full
                pool_timeout=30,  # Seconds to wait before giving up on getting a connection
                pool_recycle=1800,  # Recycle connections after 30 minutes
                connect_args={
                    "connect_timeout": 10,  # Timeout for establishing new connections
                    "keepalives": 1,  # Enable TCP keepalive
                    "keepalives_idle": 60,  # Seconds between TCP keepalive probes
                    "keepalives_interval": 10,  # Seconds between keepalive probes
                    "keepalives_count": 5,  # Failed keepalive probes before dropping connection
                },
                **kwargs
            )
            # Test the connection
            conn = engine.connect()
            conn.close()
            return engine
        except DBAPIError as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(1 * (attempt + 1))  # Exponential backoff


SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

engine = create_engine_with_retries(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    except DBAPIError:
        db.rollback()  # Rollback failed transactions
        raise
    finally:
        db.close()


# Enable foreign keys for SQLite
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
