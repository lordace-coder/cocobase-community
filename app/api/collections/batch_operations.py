"""
Batch operations for optimized bulk document creation.

OPTIMIZED: Phase 3 - Batch insert optimization for better performance.
"""

from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import insert
from app.models.collections import Document, Collection
import uuid
from datetime import datetime


def bulk_create_documents(
    db: Session,
    collection: Collection,
    documents_data: List[Dict[str, Any]],
    user_id: str = None
) -> List[Document]:
    """
    Bulk create documents using SQLAlchemy bulk insert for better performance.

    OPTIMIZED: Uses bulk_insert_mappings instead of individual inserts.

    Args:
        db: Database session
        collection: Collection to insert documents into
        documents_data: List of document data dictionaries
        user_id: Optional user ID for user-specific documents

    Returns:
        List of created Document objects
    """
    if not documents_data:
        return []

    # Prepare bulk insert data
    insert_data = []
    created_ids = []

    for doc_data in documents_data:
        doc_id = str(uuid.uuid4())
        created_ids.append(doc_id)

        insert_data.append({
            "id": doc_id,
            "collection_id": collection.id,
            "data": doc_data,
            "user_id": user_id,
            "created_at": datetime.utcnow(),
        })

    # Bulk insert all documents at once
    db.bulk_insert_mappings(Document, insert_data)
    db.commit()

    # Fetch the created documents
    created_documents = (
        db.query(Document)
        .filter(Document.id.in_(created_ids))
        .all()
    )

    return created_documents


def bulk_update_documents(
    db: Session,
    document_ids: List[str],
    update_data: Dict[str, Any]
) -> int:
    """
    Bulk update multiple documents with the same data.

    OPTIMIZED: Uses bulk update instead of individual updates.

    Args:
        db: Database session
        document_ids: List of document IDs to update
        update_data: Data to update

    Returns:
        Number of documents updated
    """
    if not document_ids:
        return 0

    # Prepare bulk update
    update_mappings = []
    for doc_id in document_ids:
        update_mappings.append({
            "id": doc_id,
            "data": update_data,
        })

    # Bulk update all documents
    db.bulk_update_mappings(Document, update_mappings)
    db.commit()

    return len(document_ids)


def bulk_delete_documents(
    db: Session,
    collection_id: str,
    document_ids: List[str]
) -> int:
    """
    Bulk delete multiple documents at once.

    OPTIMIZED: Uses single DELETE query instead of individual deletes.

    Args:
        db: Database session
        collection_id: Collection ID
        document_ids: List of document IDs to delete

    Returns:
        Number of documents deleted
    """
    if not document_ids:
        return 0

    deleted_count = (
        db.query(Document)
        .filter(
            Document.collection_id == collection_id,
            Document.id.in_(document_ids)
        )
        .delete(synchronize_session=False)
    )

    db.commit()
    return deleted_count
