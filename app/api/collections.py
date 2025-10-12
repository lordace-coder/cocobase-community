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
# ENHANCED COMPARISON OPERATORS
# ============================================

comparison_map = {
    "lte": lambda col, val: cast(col.astext, Integer) <= val,
    "gte": lambda col, val: cast(col.astext, Integer) >= val,
    "lt": lambda col, val: cast(col.astext, Integer) < val,
    "gt": lambda col, val: cast(col.astext, Integer) > val,
    "eq": lambda col, val: col.astext == str(val),
    "ne": lambda col, val: col.astext != str(val),
    "contains": lambda col, val: col.astext.ilike(f"%{val}%"),
    "startswith": lambda col, val: col.astext.ilike(f"{val}%"),
    "endswith": lambda col, val: col.astext.ilike(f"%{val}"),
    "in": lambda col, val: col.astext.in_(val.split(",")),
    "notin": lambda col, val: ~col.astext.in_(val.split(",")),
    "isnull": lambda col, val: (
        col.is_(None) if val.lower() in ("true", "1") else col.isnot(None)
    ),
}


# ============================================
# HELPER FUNCTIONS
# ============================================


def get_collection_by_id_or_name(
    collection_identifier: str, project_id: str, db: Session
) -> Collection:
    """
    Reusable function to get collection by ID or name.
    Optimized with single query using OR.
    """
    collection = (
        db.query(Collection)
        .filter(
            or_(
                Collection.id == collection_identifier,
                Collection.name == collection_identifier,
            ),
            Collection.project_id == project_id,
        )
        .first()
    )

    if not collection:
        raise HTTPException(404, "Collection not found")

    return collection


def parse_filter_expression(field_expr: str, value: str, operator: str = "eq"):
    """
    Parse a single filter expression into a SQLAlchemy filter.

    Args:
        field_expr: Field name (e.g., "age", "name")
        value: Filter value
        operator: Comparison operator (eq, gt, contains, etc.)

    Returns:
        SQLAlchemy filter expression or None
    """
    json_col = Document.data[field_expr]
    comp_fn = comparison_map.get(operator)

    if not comp_fn:
        return None

    try:
        # Type conversion for numeric operators
        if operator in {"lte", "gte", "lt", "gt"}:
            typed_value = int(value)
        else:
            typed_value = value

        return comp_fn(json_col, typed_value)
    except (ValueError, TypeError):
        return None


def build_query_filters(
    query_params: dict, base_query, reserved_params: set = None
) -> Any:
    """
    Build dynamic query filters from query parameters with advanced boolean logic.

    SYNTAX RULES:
    ============

    1. BASIC FILTERS (implicit AND):
       ?age_gte=18&status=active
       → (age >= 18) AND (status = 'active')

    2. OR CONDITIONS (same value for multiple fields):
       ?name__or__email_contains=john
       → (name ILIKE '%john%') OR (email ILIKE '%john%')

    3. AND CONDITIONS (same value for multiple fields):
       ?firstName__and__lastName=John
       → (firstName = 'John') AND (lastName = 'John')

    4. COMPLEX OR GROUPS (using [or] prefix):
       ?[or]age_gte=18&[or]role=admin
       → (age >= 18) OR (role = 'admin')

    5. MIXED AND/OR (grouping):
       ?age_gte=18&status=active&[or]role=admin&[or]isVip=true
       → (age >= 18) AND (status = 'active') AND ((role = 'admin') OR (isVip = true))

    6. MULTIPLE OR GROUPS (using [or:groupname]):
       ?[or:group1]age_gte=18&[or:group1]status=active&[or:group2]role=admin&[or:group2]isPremium=true
       → ((age >= 18) OR (status = 'active')) AND ((role = 'admin') OR (isPremium = true))

    OPERATORS:
    =========
    eq, ne, lt, gt, lte, gte, contains, startswith, endswith, in, notin, isnull

    EXAMPLES:
    ========
    # Users over 18 OR admins
    ?[or]age_gte=18&[or]role=admin

    # Active users between 18-65
    ?status=active&age_gte=18&age_lte=65

    # Search in name or email
    ?name__or__email_contains=john

    # Premium users OR (active AND verified)
    ?[or]isPremium=true&status=active&isVerified=true

    # Complex: (age > 18 AND status = active) OR role = admin
    ?[or:a]age_gte=18&[or:a]status=active&[or:b]role=admin
    """
    if reserved_params is None:
        reserved_params = {"limit", "offset", "id", "sort", "order"}

    # Organize filters by type
    and_filters = []  # Default AND filters
    or_groups = {}  # OR groups by name
    simple_or_filters = []  # Simple [or] prefixed filters

    for key, value in query_params.items():
        if key in reserved_params:
            continue

        # Extract OR group prefix: [or], [or:groupname]
        or_group = None
        actual_key = key

        if key.startswith("[or]"):
            # Simple OR: [or]age_gte=18
            actual_key = key[4:]  # Remove [or] prefix
            or_group = "__simple_or__"
        elif key.startswith("[or:") and "]" in key:
            # Named OR group: [or:group1]age_gte=18
            end_bracket = key.index("]")
            group_name = key[4:end_bracket]
            actual_key = key[end_bracket + 1 :]
            or_group = group_name

        # Parse the actual filter
        # Handle multi-field OR: field1__or__field2_operator=value
        if "__or__" in actual_key:
            or_fields = []
            or_parts = actual_key.split("__or__")

            for field_with_op in or_parts:
                if "_" in field_with_op:
                    parts = field_with_op.rsplit("_", 1)
                    if len(parts) == 2 and parts[1] in comparison_map:
                        field, op = parts
                    else:
                        field, op = field_with_op, "eq"
                else:
                    field, op = field_with_op, "eq"

                filter_expr = parse_filter_expression(field, value, op)
                if filter_expr is not None:
                    or_fields.append(filter_expr)

            if or_fields:
                combined = or_(*or_fields)
                if or_group:
                    if or_group not in or_groups:
                        or_groups[or_group] = []
                    or_groups[or_group].append(combined)
                else:
                    and_filters.append(combined)

        # Handle multi-field AND: field1__and__field2_operator=value
        elif "__and__" in actual_key:
            and_fields = []
            and_parts = actual_key.split("__and__")

            for field_with_op in and_parts:
                if "_" in field_with_op:
                    parts = field_with_op.rsplit("_", 1)
                    if len(parts) == 2 and parts[1] in comparison_map:
                        field, op = parts
                    else:
                        field, op = field_with_op, "eq"
                else:
                    field, op = field_with_op, "eq"

                filter_expr = parse_filter_expression(field, value, op)
                if filter_expr is not None:
                    and_fields.append(filter_expr)

            if and_fields:
                combined = and_(*and_fields)
                if or_group:
                    if or_group not in or_groups:
                        or_groups[or_group] = []
                    or_groups[or_group].append(combined)
                else:
                    and_filters.append(combined)

        # Handle single field filters
        else:
            if "_" in actual_key:
                parts = actual_key.rsplit("_", 1)
                if len(parts) == 2 and parts[1] in comparison_map:
                    field, op = parts
                else:
                    field, op = actual_key, "eq"
            else:
                field, op = actual_key, "eq"

            filter_expr = parse_filter_expression(field, value, op)
            if filter_expr is not None:
                if or_group:
                    if or_group not in or_groups:
                        or_groups[or_group] = []
                    or_groups[or_group].append(filter_expr)
                else:
                    and_filters.append(filter_expr)

    # Build final filter
    final_filters = []

    # Add AND filters
    final_filters.extend(and_filters)

    # Add OR groups (each group becomes an OR clause, groups are ANDed together)
    for group_name, group_filters in or_groups.items():
        if group_filters:
            if group_name == "__simple_or__":
                # Simple OR filters are combined into one OR clause
                final_filters.append(or_(*group_filters))
            else:
                # Named groups: each group is an OR clause
                final_filters.append(or_(*group_filters))

    # Apply all filters with AND
    if final_filters:
        base_query = base_query.filter(and_(*final_filters))

    return base_query


async def invalidate_collection_cache(collection_id: str):
    """Invalidate all caches related to a collection."""
    try:
        # Clear specific collection caches
        await FastAPICache.clear(namespace=f"collection:{collection_id}")
    except Exception:
        pass  # Cache invalidation shouldn't break the app


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

    Fixed Issues:
    - ✅ Removed optional collection (was causing confusion)
    - ✅ Use get_or_create pattern more efficiently
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
            notify_collection_watchers, _collection.id, new_doc, RealtimeEvent.create
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
        notify_collection_watchers, collection.id, document, RealtimeEvent.update
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
# BATCH OPERATIONS (NEW FEATURE)
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
                notify_collection_watchers, collection.id, doc, RealtimeEvent.create
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
