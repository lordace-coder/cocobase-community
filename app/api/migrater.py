"""
Cocobase Migration Router - Simplified with Original ID Preservation
Handles database migration from external sources directly to Cocobase database
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel
from typing import List, Dict, Any, Optional, Literal
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import uuid
from datetime import datetime
from contextlib import contextmanager
import logging
import json

from app.core.database import get_db
from app.models.app_client import Project, AppUser
from app.models.collections import Collection, Document
from app.services.utils import hash_password

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/import", tags=["import"])

# In-memory storage for migration jobs (use Redis/DB in production)
migration_jobs = {}


# Models
class DatabaseConfig(BaseModel):
    type: Literal["postgresql", "mysql", "mongodb", "sqlite"]
    host: Optional[str] = None
    port: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    database: Optional[str] = None
    file_path: Optional[str] = None  # For SQLite


class TableInfo(BaseModel):
    name: str
    rows: int
    columns: List[str]
    is_user_table: bool = False
    detected_password_field: Optional[str] = None


class MigrationConfig(BaseModel):
    source_db: DatabaseConfig
    cocobase_project_id: str
    cocobase_api_key: str
    tables: List[Dict[str, Any]]
    batch_size: int = 1000
    clear_before_import: bool = True  # Clear existing data before import


class MigrationJob(BaseModel):
    id: str
    status: Literal["pending", "running", "completed", "failed"]
    progress: int = 0
    current_table: Optional[str] = None
    tables_completed: List[str] = []
    error: Optional[str] = None
    stats: Dict[str, Any] = {}
    created_at: datetime
    completed_at: Optional[datetime] = None


# Database Connection Manager
@contextmanager
def get_source_connection(config: DatabaseConfig):
    """Create connection to source database"""
    try:
        if config.type == "postgresql":
            conn_str = f"postgresql://{config.username}:{config.password}@{config.host}:{config.port}/{config.database}"
        elif config.type == "mysql":
            conn_str = f"mysql+pymysql://{config.username}:{config.password}@{config.host}:{config.port}/{config.database}"
        elif config.type == "sqlite":
            conn_str = f"sqlite:///{config.file_path}"
        else:
            raise ValueError(f"Unsupported database type: {config.type}")

        engine = create_engine(conn_str, pool_pre_ping=True, pool_recycle=3600)
        connection = engine.connect()
        yield connection
        connection.close()
        engine.dispose()
    except Exception as e:
        logger.error(f"Connection error: {str(e)}")
        raise HTTPException(
            status_code=400, detail=f"Database connection failed: {str(e)}"
        )


def detect_user_table(
    table_name: str, columns: List[str]
) -> tuple[bool, Optional[str]]:
    """
    Detect if a table is a user table and find password field
    Returns: (is_user_table, password_field_name)
    """
    table_lower = table_name.lower()
    columns_lower = [col.lower() for col in columns]

    # Check if table name suggests it's a user table
    user_indicators = ["user", "account", "member", "customer", "auth"]
    is_user_table = any(indicator in table_lower for indicator in user_indicators)

    # Check for email and password fields
    has_email = any("email" in col or "mail" in col for col in columns_lower)

    # Find password field
    password_field = None
    password_indicators = ["password", "passwd", "pwd", "pass", "hash"]
    for col, col_lower in zip(columns, columns_lower):
        if any(indicator in col_lower for indicator in password_indicators):
            password_field = col
            break

    # It's a user table if it has both email and password
    is_user_table = is_user_table and has_email and password_field is not None

    return is_user_table, password_field


def verify_project_access(db: Session, project_id: str, api_key: str) -> Project:
    """Verify that the API key is valid for the project"""
    project = (
        db.query(Project)
        .filter(
            Project.id == project_id, Project.api_key == api_key, Project.active == True
        )
        .first()
    )

    if not project:
        raise HTTPException(status_code=403, detail="Invalid project ID or API key")

    return project


# API Endpoints
@router.post("/test-connection")
async def test_connection(config: DatabaseConfig):
    """Test database connection and return table list"""
    try:
        with get_source_connection(config) as conn:
            inspector = inspect(conn)
            table_names = inspector.get_table_names()

            tables = []
            for table_name in table_names:
                columns = [col["name"] for col in inspector.get_columns(table_name)]

                # Get row count
                try:
                    result = conn.execute(text(f'SELECT COUNT(*) FROM "{table_name}"'))
                    row_count = result.scalar()
                except Exception as e:
                    logger.warning(f"Could not count rows in {table_name}: {e}")
                    row_count = 0

                # Detect if it's a user table
                is_user_table, password_field = detect_user_table(table_name, columns)

                tables.append(
                    {
                        "name": table_name,
                        "rows": row_count,
                        "columns": columns,
                        "is_user_table": is_user_table,
                        "detected_password_field": password_field,
                    }
                )

            return {
                "success": True,
                "tables": tables,
                "message": f"Found {len(tables)} tables",
            }
    except Exception as e:
        logger.error(f"Connection test failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/preview-table")
async def preview_table(config: DatabaseConfig, table_name: str, limit: int = 5):
    """Preview data from a table"""
    try:
        with get_source_connection(config) as conn:
            result = conn.execute(text(f'SELECT * FROM "{table_name}" LIMIT {limit}'))
            columns = result.keys()
            rows = []
            for row in result.fetchall():
                # Convert row to dict and handle special types
                row_dict = {}
                for col, val in zip(columns, row):
                    # Convert non-JSON-serializable types to strings
                    if isinstance(val, (datetime, bytes)):
                        row_dict[col] = str(val)
                    else:
                        row_dict[col] = val
                rows.append(row_dict)

            return {"success": True, "columns": list(columns), "rows": rows}
    except Exception as e:
        logger.error(f"Preview failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/start")
async def start_migration(
    migration_config: MigrationConfig,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Start migration process in background"""

    # Verify project access
    verify_project_access(
        db, migration_config.cocobase_project_id, migration_config.cocobase_api_key
    )

    job_id = str(uuid.uuid4())

    job = MigrationJob(id=job_id, status="pending", created_at=datetime.utcnow())

    migration_jobs[job_id] = job.dict()

    # Start migration in background
    background_tasks.add_task(run_migration, job_id, migration_config)

    return {"success": True, "job_id": job_id, "message": "Migration started"}


@router.get("/status/{job_id}")
async def get_migration_status(job_id: str):
    """Get migration job status"""
    if job_id not in migration_jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    return migration_jobs[job_id]


def clear_collection_data(db: Session, collection_id: str):
    """Clear all documents from a collection"""
    try:
        deleted_count = (
            db.query(Document)
            .filter(Document.collection_id == collection_id)
            .delete(synchronize_session=False)
        )
        db.commit()
        db.flush()  # Ensure changes are flushed
        logger.info(
            f"Cleared {deleted_count} documents from collection {collection_id}"
        )
    except Exception as e:
        logger.error(f"Failed to clear collection data: {str(e)}")
        db.rollback()
        raise


def clear_project_users(db: Session, project_id: str):
    """Clear all users from a project"""
    try:
        deleted_count = (
            db.query(AppUser)
            .filter(AppUser.client_id == project_id)
            .delete(synchronize_session=False)
        )
        db.commit()
        db.flush()  # Ensure changes are flushed
        logger.info(f"Cleared {deleted_count} users from project {project_id}")
    except Exception as e:
        logger.error(f"Failed to clear users: {str(e)}")
        db.rollback()
        raise


def run_migration(job_id: str, config: MigrationConfig):
    """Background task to run the actual migration"""
    from app.core.database import SessionLocal

    job = migration_jobs[job_id]
    job["status"] = "running"

    total_tables = len(config.tables)
    tables_migrated = 0
    total_records = 0

    db = SessionLocal()

    try:
        # Verify project exists
        project = verify_project_access(
            db, config.cocobase_project_id, config.cocobase_api_key
        )

        for table_config in config.tables:
            table_name = table_config["name"]
            is_user_table = table_config.get("is_user_table", False)
            password_field = table_config.get("password_field")
            collection_name = table_config.get("collection_name", table_name)
            selected_columns = table_config.get("columns", [])

            job["current_table"] = table_name

            # Create collection or prepare for user migration
            if is_user_table:
                collection_id = None
                # Clear existing users if configured
                if config.clear_before_import:
                    clear_project_users(db, project.id)
                    logger.info(f"Cleared existing users before migration")
            else:
                collection_id = create_cocobase_collection(
                    db, project.id, collection_name
                )
                # Clear existing documents if configured
                if config.clear_before_import:
                    clear_collection_data(db, collection_id)
                    logger.info(
                        f"Cleared collection {collection_name} before migration"
                    )

            # Migrate data in batches - create fresh connection for each table
            offset = 0
            records_migrated = 0

            # Use a fresh connection for each table to avoid timeouts
            with get_source_connection(config.source_db) as conn:
                while True:
                    # Fetch batch from source
                    column_str = (
                        ", ".join([f'"{col}"' for col in selected_columns])
                        if selected_columns
                        else "*"
                    )
                    query = text(
                        f'SELECT {column_str} FROM "{table_name}" '
                        f"LIMIT {config.batch_size} OFFSET {offset}"
                    )
                    result = conn.execute(query)
                    rows = result.fetchall()

                    if not rows:
                        break

                    columns = result.keys()
                    records = []
                    for row in rows:
                        row_dict = {}
                        for col, val in zip(columns, row):
                            # Convert non-JSON-serializable types
                            if isinstance(val, datetime):
                                row_dict[col] = val.isoformat()
                            elif isinstance(val, bytes):
                                row_dict[col] = val.decode("utf-8", errors="ignore")
                            else:
                                row_dict[col] = val
                        records.append(row_dict)

                    # Insert into Cocobase
                    if is_user_table:
                        migrate_users_to_cocobase(
                            db, project.id, records, password_field
                        )
                    else:
                        migrate_documents_to_cocobase(db, collection_id, records)

                    records_migrated += len(records)
                    offset += config.batch_size

                    # Update progress
                    if table_config["rows"] > 0:
                        progress = int(
                            (
                                (
                                    tables_migrated
                                    + (records_migrated / table_config["rows"])
                                )
                                / total_tables
                            )
                            * 100
                        )
                        job["progress"] = min(progress, 99)

            tables_migrated += 1
            total_records += records_migrated
            job["tables_completed"].append(table_name)
            job["progress"] = int((tables_migrated / total_tables) * 100)

        # Mark as completed
        job["status"] = "completed"
        job["progress"] = 100
        job["completed_at"] = datetime.utcnow()
        job["stats"] = {
            "tables": tables_migrated,
            "records": total_records,
            "duration": (datetime.utcnow() - job["created_at"]).total_seconds(),
        }

    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        job["status"] = "failed"
        job["error"] = str(e)
    finally:
        db.close()


def create_cocobase_collection(
    db: Session, project_id: str, collection_name: str
) -> str:
    """Create a collection in Cocobase database"""

    # Check if collection already exists
    existing = (
        db.query(Collection)
        .filter(Collection.project_id == project_id, Collection.name == collection_name)
        .first()
    )


    if existing:
        # delete if exists
        db.delete(existing)
        db.commit()
        logger.info(f"Deleted existing collection: {collection_name} ({existing.id})")

    # Create new collection
    collection = Collection(
        id=str(uuid.uuid4()),
        name=collection_name,
        project_id=project_id,
        created_at=datetime.utcnow(),
        permissions={"create": [], "read": [], "update": [], "delete": []},
    )

    db.add(collection)
    db.commit()
    db.refresh(collection)

    logger.info(f"Created collection: {collection_name} ({collection.id})")
    return collection.id


def migrate_users_to_cocobase(
    db: Session, project_id: str, users: List[Dict], password_field: str
):
    """Migrate users to Cocobase app_users table preserving original IDs"""

    for user in users:
        try:
            # Extract user data
            email = user.get("email") or user.get("Email") or user.get("EMAIL")
            original_id = user.get("id") or user.get("Id") or user.get("ID")

            if not email:
                logger.warning(f"Skipping user without email: {user}")
                continue

            # Use original ID or generate new one
            user_id = str(original_id) if original_id else str(uuid.uuid4())

            # Get password hash (already hashed in source DB)
            password_hash = user.get(password_field, "")

            # Remove password, email, and id from data to avoid duplication
            user_data = {
                k: v
                for k, v in user.items()
                if k.lower() not in [password_field.lower(), "email", "password", "id"]
            }

            # Create app_user with original ID and password hash
            app_user = AppUser(
                id=user_id,
                client_id=project_id,
                email=email,
                password=(
                    password_hash  # Use existing hash directly (don't re-hash!)
                    if password_hash
                    else hash_password("changeme123")  # Only hash default password
                ),
                data=user_data,
                created_at=datetime.utcnow(),
                roles=[],
            )

            db.add(app_user)
            db.commit()

            logger.info(f"Migrated user: {email} (ID: {user_id})")

        except Exception as e:
            logger.error(
                f"Failed to migrate user {user.get('email', 'unknown')}: {str(e)}"
            )
            db.rollback()
            # Continue with next user instead of failing entire migration
            continue


def migrate_documents_to_cocobase(
    db: Session, collection_id: str, documents: List[Dict]
):
    """Migrate documents to Cocobase collection preserving original IDs"""

    for doc in documents:
        try:
            # Get original ID
            original_id = doc.get("id") or doc.get("Id") or doc.get("ID")

            # Use original ID or generate new one
            doc_id = str(original_id) 

            # Remove id from data (we're using it as the document ID)
            doc_data = {k: v for k, v in doc.items() if k.lower() != "id"}
            doc_data['old_id'] = doc_id  # Store original ID in data for reference
            document = Document(
                id=str(uuid.uuid4()),
                collection_id=collection_id,
                data=doc_data,
                created_at=datetime.utcnow(),
            )

            db.add(document)

        except Exception as e:
            logger.error(f"Failed to add document {doc.get('id', 'unknown')}: {str(e)}")
            db.rollback()
            raise

    # Commit all documents in batch
    try:
        db.commit()
        logger.info(
            f"Migrated {len(documents)} documents to collection {collection_id}"
        )
    except Exception as e:
        logger.error(f"Failed to commit documents batch: {str(e)}")
        db.rollback()
        raise
