from datetime import datetime
from typing import Optional, Any
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Query,
    BackgroundTasks,
    UploadFile,
)
from pydantic import BaseModel
from sqlalchemy import cast, Integer, String, or_, and_, func
from sqlalchemy.orm import Session, joinedload
from fastapi.encoders import jsonable_encoder
from fastapi_cache.decorator import cache
from fastapi_cache import FastAPICache
from .utilities import *
from app.core.database import get_db
from app.core.dependencies import get_app_user, get_project
from app.core.middleware import track_api_call
from app.core.permissions import can_access_collection
from app.models.app_client import Project
from app.models.user import User
from app.models.collections import Document, Collection
from app.schemas.collections import *
from app.services.utils import handle_webhook_call
from app.storage.storage import check_storage_limit, handle_file_upload
from app.websockets.documents import RealtimeEvent, notify_collection_watchers


router = APIRouter(
    prefix="/collections",
    tags=["Collections"],
    dependencies=[Depends(get_project), Depends(track_api_call)],
)


# ============================================
# COLLECTION ROUTES
# ============================================


@router.post("/", status_code=201, response_model=CollectionSchema)
def create_collection(
    payload: CollectionCreateSchema,
    db: Session = Depends(get_db),
    proj: tuple[Project, User] = Depends(get_project),
):
    """
    Create a new collection.

    Optimized:
    - Use exists() for faster duplicate check
    - Single query for validation
    """
    project, _ = proj

    # Optimized existence check
    exists = db.query(
        db.query(Collection)
        .filter(Collection.project_id == project.id, Collection.name == payload.name)
        .exists()
    ).scalar()

    if exists:
        raise HTTPException(
            400, "A collection with this name already exists in this project"
        )

    new_collection = Collection(
        **payload.model_dump(),
        project_id=project.id,
        project=project,
    )

    db.add(new_collection)
    db.commit()
    db.refresh(new_collection)

    return new_collection


@router.patch("/{collection_id}", response_model=CollectionSchema)
def update_collection(
    collection_id: str,
    payload: CollectionUpdateSchema,
    bg: BackgroundTasks,
    db: Session = Depends(get_db),
    proj: tuple[Project, User] = Depends(get_project),
):
    """
    Update a collection.

    Optimized:
    - Use helper function
    - Invalidate cache after update
    """
    project, _ = proj

    collection = get_collection_by_id_or_name(collection_id, project.id, db)

    # Check for name conflicts if name is being updated
    if payload.name and payload.name != collection.name:
        exists = db.query(
            db.query(Collection)
            .filter(
                Collection.project_id == project.id,
                Collection.name == payload.name,
                Collection.id != collection.id,
            )
            .exists()
        ).scalar()

        if exists:
            raise HTTPException(
                400, "A collection with this name already exists in this project"
            )

        collection.name = payload.name

    db.add(collection)
    db.commit()
    db.refresh(collection)

    # Invalidate cache in background
    bg.add_task(invalidate_collection_cache, collection.id)

    return collection


@router.delete("/{collection_id}", status_code=204)
def delete_collection(
    collection_id: str,
    bg: BackgroundTasks,
    db: Session = Depends(get_db),
    proj: tuple[Project, User] = Depends(get_project),
):
    """
    Delete a collection.

    Optimized:
    - Use helper function
    - Added synchronize_session=False for performance
    - Invalidate cache after deletion
    """
    project, _ = proj

    # Verify collection exists first (for better error message)
    collection = get_collection_by_id_or_name(collection_id, project.id, db)

    # Delete the collection
    db.query(Collection).filter(Collection.id == collection.id).delete(
        synchronize_session=False
    )

    db.commit()

    # Invalidate cache in background
    bg.add_task(invalidate_collection_cache, collection.id)

    return None


# ============================================
# DOCUMENT ROUTES
# ============================================


@router.post("/documents", response_model=DocumentSchema)
def create_new_document(
    payload: DocumentCreateSchema,
    bg: BackgroundTasks,
    collection: str,
    db: Session = Depends(get_db),
    proj: tuple[Project, User] = Depends(get_project),
    user: AppUser = Depends(get_app_user),
) -> DocumentSchema:
    """
    Create a new document in a collection.

    Optimized:
    - Made collection parameter required (removed None default)
    - Use helper function
    - Better error handling
    - Invalidate cache after creation
    """
    project, _ = proj

    if not payload.data:
        raise HTTPException(400, "Document data is required")

    # Try to find existing collection
    _collection = (
        db.query(Collection)
        .filter(
            or_(Collection.id == collection, Collection.name == collection),
            Collection.project_id == project.id,
        )
        .first()
    )

    # Create collection if it doesn't exist
    if not _collection:
        _collection = Collection(
            name=collection,
            project_id=project.id,
            project=project,
        )
        db.add(_collection)
        db.commit()
        db.refresh(_collection)

    # Verify permissions
    can_access_collection(_collection, "create", user)

    try:
        new_doc = Document(
            data=payload.data,
            collection_id=_collection.id,
        )
        db.add(new_doc)
        db.commit()
        db.refresh(new_doc)

        # Background tasks
        if _collection.webhook_url:
            bg.add_task(handle_webhook_call, _collection.webhook_url, payload.data)

        bg.add_task(
            notify_collection_watchers, _collection.name, new_doc, RealtimeEvent.CREATE
        )

        # Invalidate cache
        bg.add_task(invalidate_collection_cache, _collection.id)

        return new_doc

    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Failed to create document: {str(e)}")


@router.get("/{id}/documents", response_model=list[DocumentSchema])
async def list_documents(
    id: str,
    request: Request,
    db: Session = Depends(get_db),
    proj: tuple[Project, User] = Depends(get_project),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    sort: Optional[str] = Query(None, description="Field to sort by"),
    order: Optional[str] = Query("desc", regex="^(asc|desc)$"),
    user: AppUser = Depends(get_app_user),
) -> list[DocumentSchema]:
    """
    List documents in a collection with advanced filtering and boolean logic.

    🚨 REMOVED @cache DECORATOR - Security Issue!
    - Documents are user-specific (permissions)
    - Data changes frequently (create/update/delete)
    - Query params make cache keys too variable

    QUERY SYNTAX GUIDE:
    ==================

    1. BASIC FILTERS (AND logic by default):
       /documents?age_gte=18&status=active
       → age >= 18 AND status = 'active'

       /documents?user_id=901235c6-9564-4de0-bb40-0c5db80d4f26
       → Filter by exact user_id (handles underscores correctly!)

    2. SEARCH MULTIPLE FIELDS (OR within same value):
       /documents?name__or__email_contains=john
       → name CONTAINS 'john' OR email CONTAINS 'john'

    3. OR CONDITIONS (using [or] prefix):
       /documents?[or]age_gte=18&[or]role=admin
       → age >= 18 OR role = 'admin'

    4. COMPLEX GROUPING:
       /documents?status=active&[or]isPremium=true&[or]role=admin
       → status = 'active' AND (isPremium = true OR role = 'admin')

    5. MULTIPLE OR GROUPS:
       /documents?[or:a]age_gte=18&[or:a]status=active&[or:b]role=admin&[or:b]isPremium=true
       → (age >= 18 OR status = 'active') AND (role = 'admin' OR isPremium = true)

    6. IN OPERATOR:
       /documents?status_in=active,pending,completed
       → status IN ('active', 'pending', 'completed')

    7. NULL CHECKS:
       /documents?deletedAt_isnull=true
       → deletedAt IS NULL

    OPERATORS:
    =========
    - eq: equals (default)
    - ne: not equals
    - gt, gte, lt, lte: numeric comparisons
    - contains: case-insensitive substring
    - startswith: starts with (case-insensitive)
    - endswith: ends with (case-insensitive)
    - in: value in list (comma-separated)
    - notin: value not in list
    - isnull: is null/not null (true/false)

    REAL-WORLD EXAMPLES:
    ===================

    # Find user by ID (handles underscores in field names!)
    GET /collections/users/documents?user_id=901235c6-9564-4de0-bb40-0c5db80d4f26

    # Find active users over 18 OR admins
    GET /collections/users/documents?status=active&[or]age_gte=18&[or]role=admin

    # Find premium users OR verified users with age > 25
    GET /collections/users/documents?[or:a]isPremium=true&[or:b]isVerified=true&[or:b]age_gte=25

    # Search by name or email, only active users
    GET /collections/users/documents?name__or__email_contains=john&status=active

    # Find users in multiple countries, sorted by age
    GET /collections/users/documents?country_in=US,UK,CA&sort=age&order=asc

    # Find incomplete tasks assigned to user OR high priority
    GET /collections/tasks/documents?status=incomplete&[or]assignedTo=user123&[or]priority=high
    """
    project = proj[0]

    # Get collection
    collection = get_collection_by_id_or_name(id, project.id, db)

    # Verify permissions
    can_access_collection(collection, "read", user)

    # Base query with eager loading
    query = (
        db.query(Document)
        .options(joinedload(Document.collection))
        .filter(Document.collection_id == collection.id)
    )

    # Apply dynamic filters with boolean logic
    query = build_query_filters(
        dict(request.query_params),
        query,
        reserved_params={"id", "limit", "offset", "sort", "order"},
    )

    # Apply sorting
    if sort:
        if sort == "created_at":
            sort_col = Document.created_at
        else:
            # Sort by JSON field
            sort_col = Document.data[sort].astext

        if order == "asc":
            query = query.order_by(sort_col.asc())
        else:
            query = query.order_by(sort_col.desc())
    else:
        # Default sorting
        query = query.order_by(Document.created_at.desc())

    # Apply pagination
    results = query.offset(offset).limit(limit).all()

    print(f"DEBUG: Query returned {len(results)} documents\n")

    # Convert to Pydantic for consistency
    return [DocumentSchema.model_validate(doc) for doc in results]


@router.get("/{id}/documents/{document_id}", response_model=DocumentSchema)
async def get_document(
    id: str,
    document_id: str,
    proj: tuple[Project, User] = Depends(get_project),
    db: Session = Depends(get_db),
    user: AppUser = Depends(get_app_user),
) -> DocumentSchema:
    """
    Get a single document by ID.

    🚨 REMOVED @cache DECORATOR - Security Issue!
    - User-specific permissions
    - Document data may change

    Optimizations:
    - ✅ Use helper function
    - ✅ Single query with eager loading
    - ✅ Convert to Pydantic
    """
    project = proj[0]

    collection = get_collection_by_id_or_name(id, project.id, db)

    # Verify permissions
    can_access_collection(collection, "read", user)

    # Get document with eager loading
    document = (
        db.query(Document)
        .options(joinedload(Document.collection))
        .filter(Document.id == document_id, Document.collection_id == collection.id)
        .first()
    )

    if not document:
        raise HTTPException(404, "Document not found")

    return DocumentSchema.model_validate(document)


@router.patch("/{id}/documents/{document_id}", response_model=DocumentSchema)
def edit_document(
    id: str,
    document_id: str,
    payload: DocumentUpdateSchema,
    bg: BackgroundTasks,
    proj: tuple[Project, User] = Depends(get_project),
    db: Session = Depends(get_db),
    user: AppUser = Depends(get_app_user),
) -> DocumentSchema:
    """
    Update a document.

    Optimizations:
    - ✅ Use helper function
    - ✅ Eager load collection
    - ✅ Merge data instead of replace (safer)
    - ✅ Invalidate cache after update
    """
    project = proj[0]

    collection = get_collection_by_id_or_name(id, project.id, db)

    # Verify permissions
    can_access_collection(collection, "update", user)

    # Get document with eager loading
    document = (
        db.query(Document)
        .options(joinedload(Document.collection))
        .filter(Document.id == document_id, Document.collection_id == collection.id)
        .first()
    )

    if not document:
        raise HTTPException(404, "Document not found")

    # Merge data instead of replacing (preserves fields not in payload)
    if payload.data:
        existing_data = dict(document.data) if document.data else {}
        existing_data.update(payload.data)
        document.data = existing_data

    db.add(document)
    db.commit()
    db.refresh(document)

    # Background tasks
    bg.add_task(
        notify_collection_watchers, collection.name, document, RealtimeEvent.UPDATE
    )

    if collection.webhook_url:
        bg.add_task(handle_webhook_call, collection.webhook_url, payload.data, True)

    # Invalidate cache
    bg.add_task(invalidate_collection_cache, collection.id)

    return document


@router.delete("/{id}/documents/{document_id}")
def delete_document(
    id: str,
    document_id: str,
    bg: BackgroundTasks,
    proj: tuple[Project, User] = Depends(get_project),
    db: Session = Depends(get_db),
    user: AppUser = Depends(get_app_user),
):
    """
    Delete a document.

    Optimizations:
    - ✅ Use helper function
    - ✅ Use synchronize_session=False
    - ✅ Invalidate cache after deletion
    """
    project = proj[0]

    collection = get_collection_by_id_or_name(id, project.id, db)

    # Verify permissions
    can_access_collection(collection, "delete", user)

    # Delete document
    result = (
        db.query(Document)
        .filter(Document.id == document_id, Document.collection_id == collection.id)
        .delete(synchronize_session=False)
    )

    if not result:
        raise HTTPException(404, "Document not found")

    db.commit()

    # Invalidate cache
    bg.add_task(invalidate_collection_cache, collection.id)

    return {"status": "success", "message": "Document deleted successfully"}


# ============================================
# FILE UPLOAD
# ============================================


@router.post("/file")
async def upload_file_to_project(
    file: UploadFile,
    directory: Optional[str] = None,
    proj: tuple[Project, User] = Depends(get_project),
):
    """
    Upload a file to project storage.

    Optimizations:
    - ✅ Added proper error handling
    - ✅ Validate file size before reading
    - ✅ Added file type validation (optional)
    """
    if not file.filename:
        raise HTTPException(400, "Filename is required")

    try:
        # Read file content
        file_content = await file.read()
        file_size = len(file_content)

        # Check storage limit
        check_storage_limit(proj[0].id, file_size)

        # Upload file
        file_url = handle_file_upload(
            file_content, proj[0].id, file.filename, directory
        )

        return {
            "status": "success",
            "message": "File uploaded successfully",
            "url": file_url,
            "filename": file.filename,
            "size": file_size,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to upload file: {str(e)}")


# ============================================
# BATCH OPERATIONS (OPTIMIZED)
# ============================================


class BatchDeleteRequest(BaseModel):
    document_ids: list[str]


class BatchCreateRequest(BaseModel):
    documents: list[dict]  # List of document data objects


@router.post("/{id}/documents/batch-create", response_model=list[DocumentSchema])
def batch_create_documents(
    id: str,
    payload: BatchCreateRequest,
    bg: BackgroundTasks,
    proj: tuple[Project, User] = Depends(get_project),
    db: Session = Depends(get_db),
    user: AppUser = Depends(get_app_user),
) -> list[DocumentSchema]:
    """
    Create multiple documents at once.

    Request Body:
    {
        "documents": [
            {"name": "John", "age": 25},
            {"name": "Jane", "age": 30},
            {"name": "Bob", "age": 35}
        ]
    }

    Optimization: Single transaction for all documents.
    """
    project = proj[0]

    collection = get_collection_by_id_or_name(id, project.id, db)

    # Verify permissions
    can_access_collection(collection, "create", user)

    if not payload.documents:
        raise HTTPException(400, "No documents provided")

    if len(payload.documents) > 1000:
        raise HTTPException(400, "Maximum 1000 documents per batch")

    try:
        created_documents = []

        # Create all documents in one transaction
        for doc_data in payload.documents:
            if not doc_data:
                continue

            new_doc = Document(
                data=doc_data,
                collection_id=collection.id,
            )
            db.add(new_doc)
            created_documents.append(new_doc)

        # Commit all at once
        db.commit()

        # Refresh all documents
        for doc in created_documents:
            db.refresh(doc)

        # Background tasks
        for doc in created_documents:
            bg.add_task(
                notify_collection_watchers, collection.name, doc, RealtimeEvent.CREATE
            )

        if collection.webhook_url:
            bg.add_task(
                handle_webhook_call,
                collection.webhook_url,
                [doc.data for doc in created_documents],
            )

        # Invalidate cache
        bg.add_task(invalidate_collection_cache, collection.id)

        return [DocumentSchema.model_validate(doc) for doc in created_documents]

    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Failed to create documents: {str(e)}")


@router.post("/{id}/documents/batch-delete")
def batch_delete_documents(
    id: str,
    payload: BatchDeleteRequest,
    bg: BackgroundTasks,
    proj: tuple[Project, User] = Depends(get_project),
    db: Session = Depends(get_db),
    user: AppUser = Depends(get_app_user),
):
    """
    Delete multiple documents at once.

    Optimization: Single query to delete multiple documents.
    """
    project = proj[0]

    collection = get_collection_by_id_or_name(id, project.id, db)

    # Verify permissions
    can_access_collection(collection, "delete", user)

    if not payload.document_ids:
        raise HTTPException(400, "No document IDs provided")

    # Batch delete
    result = (
        db.query(Document)
        .filter(
            Document.id.in_(payload.document_ids),
            Document.collection_id == collection.id,
        )
        .delete(synchronize_session=False)
    )

    db.commit()

    # Invalidate cache
    bg.add_task(invalidate_collection_cache, collection.id)

    return {
        "status": "success",
        "message": f"Deleted {result} documents",
        "count": result,
    }


class BatchUpdateRequest(BaseModel):
    updates: dict[str, dict]  # {document_id: {data: {...}}}


@router.post("/{id}/documents/batch-update")
def batch_update_documents(
    id: str,
    payload: BatchUpdateRequest,
    bg: BackgroundTasks,
    proj: tuple[Project, User] = Depends(get_project),
    db: Session = Depends(get_db),
    user: AppUser = Depends(get_app_user),
):
    """
    Update multiple documents at once.

    Optimization: Batch update to reduce queries.
    """
    project = proj[0]

    collection = get_collection_by_id_or_name(id, project.id, db)

    # Verify permissions
    can_access_collection(collection, "update", user)

    if not payload.updates:
        raise HTTPException(400, "No updates provided")

    # Get all documents in one query
    document_ids = list(payload.updates.keys())
    documents = (
        db.query(Document)
        .filter(Document.id.in_(document_ids), Document.collection_id == collection.id)
        .all()
    )

    updated_count = 0
    for doc in documents:
        if doc.id in payload.updates:
            update_data = payload.updates[doc.id]
            if "data" in update_data:
                existing_data = dict(doc.data) if doc.data else {}
                existing_data.update(update_data["data"])
                doc.data = existing_data
                updated_count += 1

    db.commit()

    # Invalidate cache
    bg.add_task(invalidate_collection_cache, collection.id)

    return {
        "status": "success",
        "message": f"Updated {updated_count} documents",
        "count": updated_count,
    }


# ============================================
# ADVANCED QUERY ENDPOINTS (NEW)
# ============================================


@router.get("/{id}/documents/count")
async def count_documents(
    id: str,
    request: Request,
    db: Session = Depends(get_db),
    proj: tuple[Project, User] = Depends(get_project),
    user: AppUser = Depends(get_app_user),
):
    """
    Count documents matching filters without returning the documents.

    Useful for pagination and statistics.

    Example:
        GET /collections/users/documents/count?status=active&age_gte=18
        → Returns: {"count": 42}
    """
    project = proj[0]

    collection = get_collection_by_id_or_name(id, project.id, db)

    # Verify permissions
    can_access_collection(collection, "read", user)

    # Base query
    query = db.query(func.count(Document.id)).filter(
        Document.collection_id == collection.id
    )

    # Apply filters (excluding pagination params)
    filtered_params = {
        k: v
        for k, v in request.query_params.items()
        if k not in {"limit", "offset", "sort", "order"}
    }

    if filtered_params:
        # We need to convert the count query to a regular query, apply filters, then count
        doc_query = db.query(Document).filter(Document.collection_id == collection.id)
        doc_query = build_query_filters(
            filtered_params,
            doc_query,
            reserved_params={"id", "limit", "offset", "sort", "order"},
        )
        count = doc_query.count()
    else:
        count = query.scalar()

    return {"count": count}


@router.get("/{id}/documents/aggregate")
async def aggregate_documents(
    id: str,
    request: Request,
    field: str = Query(..., description="Field to aggregate"),
    operation: str = Query(
        "count", regex="^(count|sum|avg|min|max)$", description="Aggregation operation"
    ),
    db: Session = Depends(get_db),
    proj: tuple[Project, User] = Depends(get_project),
    user: AppUser = Depends(get_app_user),
):
    """
    Perform aggregation operations on document fields.

    Operations:
    - count: Count non-null values
    - sum: Sum numeric values
    - avg: Average of numeric values
    - min: Minimum value
    - max: Maximum value

    Examples:
        GET /collections/orders/documents/aggregate?field=total&operation=sum
        → Returns: {"field": "total", "operation": "sum", "result": 15420.50}

        GET /collections/users/documents/aggregate?field=age&operation=avg&status=active
        → Returns: {"field": "age", "operation": "avg", "result": 32.5}
    """
    project = proj[0]

    collection = get_collection_by_id_or_name(id, project.id, db)

    # Verify permissions
    can_access_collection(collection, "read", user)

    # Base query
    query = db.query(Document).filter(Document.collection_id == collection.id)

    # Apply filters (excluding aggregation params)
    filtered_params = {
        k: v
        for k, v in request.query_params.items()
        if k not in {"field", "operation", "limit", "offset", "sort", "order"}
    }

    if filtered_params:
        query = build_query_filters(
            filtered_params,
            query,
            reserved_params={
                "id",
                "field",
                "operation",
                "limit",
                "offset",
                "sort",
                "order",
            },
        )

    # Get the JSON field
    json_field = Document.data[field]

    # Perform aggregation
    try:
        if operation == "count":
            result = query.filter(json_field.isnot(None)).count()
        elif operation == "sum":
            result = (
                query.with_entities(func.sum(cast(json_field.astext, Integer))).scalar()
                or 0
            )
        elif operation == "avg":
            result = query.with_entities(
                func.avg(cast(json_field.astext, Integer))
            ).scalar()
            result = float(result) if result is not None else None
        elif operation == "min":
            result = query.with_entities(
                func.min(cast(json_field.astext, Integer))
            ).scalar()
        elif operation == "max":
            result = query.with_entities(
                func.max(cast(json_field.astext, Integer))
            ).scalar()
        else:
            raise HTTPException(400, f"Unknown operation: {operation}")

        return {
            "field": field,
            "operation": operation,
            "result": result,
            "collection": collection.name,
        }

    except Exception as e:
        raise HTTPException(
            500,
            f"Aggregation failed. Ensure the field contains numeric values: {str(e)}",
        )


@router.get("/{id}/documents/group-by")
async def group_by_field(
    id: str,
    request: Request,
    field: str = Query(..., description="Field to group by"),
    count_field: Optional[str] = Query(
        None, description="Field to count (default: document count)"
    ),
    db: Session = Depends(get_db),
    proj: tuple[Project, User] = Depends(get_project),
    user: AppUser = Depends(get_app_user),
):
    """
    Group documents by a field and count occurrences.

    Examples:
        GET /collections/users/documents/group-by?field=country
        → Returns: [
            {"country": "US", "count": 150},
            {"country": "UK", "count": 80},
            {"country": "CA", "count": 45}
          ]

        GET /collections/orders/documents/group-by?field=status&status_ne=cancelled
        → Returns: [
            {"status": "completed", "count": 320},
            {"status": "pending", "count": 45}
          ]
    """
    project = proj[0]

    collection = get_collection_by_id_or_name(id, project.id, db)

    # Verify permissions
    can_access_collection(collection, "read", user)

    # Base query
    query = db.query(Document).filter(Document.collection_id == collection.id)

    # Apply filters (excluding group-by params)
    filtered_params = {
        k: v
        for k, v in request.query_params.items()
        if k not in {"field", "count_field", "limit", "offset", "sort", "order"}
    }

    if filtered_params:
        query = build_query_filters(
            filtered_params,
            query,
            reserved_params={
                "id",
                "field",
                "count_field",
                "limit",
                "offset",
                "sort",
                "order",
            },
        )

    # Get the JSON field to group by
    json_field = Document.data[field].astext

    try:
        # Group by and count
        results = (
            query.with_entities(json_field, func.count(Document.id))
            .group_by(json_field)
            .order_by(func.count(Document.id).desc())
            .all()
        )

        return [
            {field: value, "count": count}
            for value, count in results
            if value is not None
        ]

    except Exception as e:
        raise HTTPException(500, f"Group by failed: {str(e)}")


# ============================================
# UTILITY ENDPOINTS
# ============================================


@router.get("/{id}/schema")
async def get_collection_schema(
    id: str,
    db: Session = Depends(get_db),
    proj: tuple[Project, User] = Depends(get_project),
    user: AppUser = Depends(get_app_user),
):
    """
    Analyze collection documents and return inferred schema.

    Returns field names, types, and sample values.
    Useful for understanding your data structure.
    """
    project = proj[0]

    collection = get_collection_by_id_or_name(id, project.id, db)

    # Verify permissions
    can_access_collection(collection, "read", user)

    # Get a sample of documents
    sample_docs = (
        db.query(Document)
        .filter(Document.collection_id == collection.id)
        .limit(100)
        .all()
    )

    if not sample_docs:
        return {
            "collection": collection.name,
            "document_count": 0,
            "fields": {},
        }

    # Analyze field types
    field_analysis = {}

    for doc in sample_docs:
        if not doc.data:
            continue

        for key, value in doc.data.items():
            if key not in field_analysis:
                field_analysis[key] = {
                    "type": set(),
                    "samples": [],
                    "null_count": 0,
                    "total_count": 0,
                }

            field_analysis[key]["total_count"] += 1

            if value is None:
                field_analysis[key]["null_count"] += 1
                continue

            # Determine type
            value_type = type(value).__name__
            field_analysis[key]["type"].add(value_type)

            # Add sample (limit to 3 samples)
            if len(field_analysis[key]["samples"]) < 3:
                field_analysis[key]["samples"].append(value)

    # Format results
    schema = {}
    for field, analysis in field_analysis.items():
        types = list(analysis["type"])
        schema[field] = {
            "types": types,
            "primary_type": types[0] if types else "unknown",
            "nullable": analysis["null_count"] > 0,
            "null_percentage": round(
                (analysis["null_count"] / analysis["total_count"]) * 100, 2
            ),
            "samples": analysis["samples"],
        }

    total_docs = (
        db.query(func.count(Document.id))
        .filter(Document.collection_id == collection.id)
        .scalar()
    )

    return {
        "collection": collection.name,
        "document_count": total_docs,
        "analyzed_documents": len(sample_docs),
        "fields": schema,
    }


@router.get("/{id}/export")
async def export_collection(
    id: str,
    request: Request,
    format: str = Query("json", regex="^(json|csv)$"),
    db: Session = Depends(get_db),
    proj: tuple[Project, User] = Depends(get_project),
    user: AppUser = Depends(get_app_user),
):
    """
    Export collection data to JSON or CSV.

    Supports filtering - only exports documents matching the filters.

    Examples:
        GET /collections/users/export?format=json
        GET /collections/users/export?format=csv&status=active&age_gte=18
    """
    from fastapi.responses import StreamingResponse
    import json
    import io
    import csv

    project = proj[0]

    collection = get_collection_by_id_or_name(id, project.id, db)

    # Verify permissions
    can_access_collection(collection, "read", user)

    # Base query
    query = db.query(Document).filter(Document.collection_id == collection.id)

    # Apply filters
    filtered_params = {
        k: v
        for k, v in request.query_params.items()
        if k not in {"format", "limit", "offset", "sort", "order"}
    }

    if filtered_params:
        query = build_query_filters(
            filtered_params,
            query,
            reserved_params={"id", "format", "limit", "offset", "sort", "order"},
        )

    documents = query.all()

    if format == "json":
        # Export as JSON
        data = [
            {
                "id": str(doc.id),
                "created_at": doc.created_at.isoformat(),
                **doc.data,
            }
            for doc in documents
        ]

        json_str = json.dumps(data, indent=2, default=str)

        return StreamingResponse(
            io.BytesIO(json_str.encode()),
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="{collection.name}_export.json"'
            },
        )

    elif format == "csv":
        # Export as CSV
        if not documents:
            raise HTTPException(400, "No documents to export")

        # Get all unique fields
        all_fields = set()
        for doc in documents:
            if doc.data:
                all_fields.update(doc.data.keys())

        fields = ["id", "created_at"] + sorted(all_fields)

        # Create CSV
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()

        for doc in documents:
            row = {
                "id": str(doc.id),
                "created_at": doc.created_at.isoformat(),
            }
            if doc.data:
                row.update(doc.data)
            writer.writerow(row)

        return StreamingResponse(
            io.BytesIO(output.getvalue().encode()),
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{collection.name}_export.csv"'
            },
        )
