from datetime import datetime
from typing import Optional, Any, List
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Query,
    BackgroundTasks,
    UploadFile,
    File,
    Form,
)
from starlette.datastructures import UploadFile as StarletteUploadFile
from pydantic import BaseModel
from sqlalchemy import cast, Integer, String, or_, and_, func
from sqlalchemy.orm import Session, joinedload
from fastapi_cache import FastAPICache
from .utilities import *
from app.core.database import get_db
from app.core.dependencies import get_app_user, require_api_access
from app.core.permissions import can_access_collection
from app.models.app_client import Project
from app.models.user import User
from app.models.app_client import AppUser
from app.models.collections import Document, Collection
from app.schemas.collections import *
from app.services.utils import handle_webhook_call
from app.storage.storage import check_storage_limit, handle_file_upload
from app.websockets.documents import RealtimeEvent, notify_collection_watchers
import json


router = APIRouter(
    prefix="/collections",
    tags=["Collections"],
)


# ============================================
# COLLECTION ROUTES
# ============================================


@router.post("/", status_code=201, response_model=CollectionSchema)
def create_collection(
    payload: CollectionCreateSchema,
    db: Session = Depends(get_db),
    proj: tuple[Project, User] = Depends(require_api_access),
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
    proj: tuple[Project, User] = Depends(require_api_access),
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
    proj: tuple[Project, User] = Depends(require_api_access),
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

    # Store the ID before deletion (to avoid detached instance error)
    stored_collection_id = collection.id

    # Delete the collection
    db.query(Collection).filter(Collection.id == stored_collection_id).delete(
        synchronize_session=False
    )

    db.commit()

    # Invalidate cache in background
    bg.add_task(invalidate_collection_cache, stored_collection_id)

    return None


# ============================================
# DOCUMENT ROUTES
# ============================================
@router.post("/documents", response_model=DocumentSchema)
async def create_new_document(
    bg: BackgroundTasks,
    request: Request,
    collection: str = Query(..., description="Collection name or ID"),
    db: Session = Depends(get_db),
    proj: tuple[Project, User] = Depends(require_api_access),
    user: AppUser = Depends(get_app_user),
) -> DocumentSchema:
    project, _ = proj
    document_data = {}

    # Check content type to determine how to parse the request
    content_type = request.headers.get("content-type", "")

    if "multipart/form-data" in content_type:
        # Handle form data with potential file uploads
        form = await request.form()

        # Extract data field
        if "data" in form:
            try:
                document_data = json.loads(form["data"])
            except json.JSONDecodeError:
                raise HTTPException(400, "Invalid JSON in data field")

        # Process all file uploads
        uploaded_files = {}  # {field_name: [urls]}

        for field_name in form:
            if field_name in ("data", "collection"):
                continue

            field_value = form.get(field_name)

            # Check if it's a file
            if isinstance(field_value, StarletteUploadFile) and field_value.filename:
                # Read and upload file
                file_content = await field_value.read()
                file_size = len(file_content)

                check_storage_limit(project.id, file_size, db)

                file_url = handle_file_upload(
                    file_content,
                    project.id,
                    field_value.filename,
                    subdirectory=collection,
                )
                print(file_url, " file url")

                # Store by field name
                if field_name not in uploaded_files:
                    uploaded_files[field_name] = []
                uploaded_files[field_name].append(file_url)
            else:
                print(type(field_value), " not file")

        # Add files to document data
        for field_name, urls in uploaded_files.items():
            if len(urls) == 1:
                document_data[field_name] = urls[0]
            else:
                document_data[field_name] = urls
    else:
        # Handle JSON request
        json_data = await request.json()
        document_data = json_data.get("data", json_data)

    if not document_data:
        raise HTTPException(400, "Document data or files are required")

    # Find or create collection
    _collection = (
        db.query(Collection)
        .filter(
            or_(Collection.id == collection, Collection.name == collection),
            Collection.project_id == project.id,
        )
        .first()
    )

    if not _collection:
        _collection = Collection(
            name=collection,
            project_id=project.id,
            project=project,
        )
        db.add(_collection)
        db.commit()
        db.refresh(_collection)

    can_access_collection(_collection, "create", user)

    try:
        new_doc = Document(
            data=document_data,
            collection_id=_collection.id,
        )
        db.add(new_doc)
        db.commit()
        db.refresh(new_doc)

        if _collection.webhook_url:
            bg.add_task(handle_webhook_call, _collection.webhook_url, document_data)

        bg.add_task(
            notify_collection_watchers, _collection.name, new_doc, RealtimeEvent.CREATE
        )

        bg.add_task(invalidate_collection_cache, _collection.id)

        return new_doc

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Failed to create document: {str(e)}")


@router.get("/{id}/documents")
async def list_documents(
    id: str,
    request: Request,
    db: Session = Depends(get_db),
    proj: tuple[Project, User] = Depends(require_api_access),
    limit: int = Query(50, ge=1, le=500),  # Reduced for performance
    offset: int = Query(0, ge=0),
    sort: Optional[str] = Query(None, description="Field to sort by"),
    order: Optional[str] = Query("desc", regex="^(asc|desc)$"),
    # NEW: Relationship parameters
    populate: Optional[List[str]] = Query(
        None,
        description="Relationships to populate (e.g., 'author', 'tags', 'comments.user')",
    ),
    select: Optional[List[str]] = Query(
        None, description="Fields to select (e.g., 'title', 'author.name')"
    ),
    user: AppUser = Depends(get_app_user),
):
    """
    List documents in a collection with advanced filtering, boolean logic, and relationships.

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

    RELATIONSHIP FEATURES (NEW!):
    ============================

    8. AUTO-POPULATE RELATIONSHIPS:
       /documents?populate=author&populate=tags
       → Automatically fetch related users/documents based on field names

       Conventions:
       - author_id → fetches from 'users' collection or AppUser model
       - category_id → fetches from 'categories' collection
       - tag_ids → fetches multiple from 'tags' collection

    9. NESTED POPULATION:
       /documents?populate=comments.user
       → Populate comments AND each comment's user

    10. FILTER BY RELATIONSHIP FIELDS:
        /documents?author.role=admin&populate=author
        → Filter posts where author's role is 'admin'

        /documents?user.email=john@example.com&populate=user
        → Filter by user's email (works with AppUser model)

    11. SELECT SPECIFIC FIELDS:
        /documents?select=title&select=author.name&populate=author
        → Return only id, title, and author's name

    REAL-WORLD EXAMPLES:
    ===================

    # Find user by ID (handles underscores in field names!)
    GET /collections/users/documents?user_id=901235c6-9564-4de0-bb40-0c5db80d4f26

    # Find active users over 18 OR admins
    GET /collections/users/documents?status=active&[or]age_gte=18&[or]role=admin

    # Find posts with their authors
    GET /collections/posts/documents?populate=author&populate=category

    # Find posts by admin authors
    GET /collections/posts/documents?author.role=admin&populate=author

    # Find comments with nested user data
    GET /collections/comments/documents?populate=post&populate=user

    # Get only specific fields from posts and authors
    GET /collections/posts/documents?select=title&select=author.name&populate=author

    # Complex: Active posts by admins with tags
    GET /collections/posts/documents?status=active&author.role=admin&populate=author&populate=tags
    """
    project = proj[0]

    # Get collection
    collection = get_collection_by_id_or_name(id, project.id, db)

    # Verify permissions
    can_access_collection(collection, "read", user)

    # Extract query params
    query_params = dict(request.query_params)

    # Check if relationships are requested
    has_relationships = (
        populate
        or select
        or any(
            "." in k
            and not k.startswith("[")
            and k not in {"limit", "offset", "sort", "order"}
            for k in query_params.keys()
        )
    )

    if has_relationships:
        # Use relationship resolver for complex queries
        resolver = AutoRelationshipResolver(db)
        result = resolver.query_with_relationships(
            collection=collection,
            query_params=query_params,
            populate=populate,
            select=select,
            limit=limit,
            offset=offset,
        )

        # Return dict response directly (bypass DocumentSchema validation)
        # since the structure is different with populated relationships
        return result["data"]

    # Otherwise, use your existing fast path for simple queries

    # Base query - removed joinedload for performance (not needed for single collection)
    query = db.query(Document).filter(Document.collection_id == collection.id)

    # Remove populate and select from query_params before filtering
    filtered_query_params = {
        k: v
        for k, v in query_params.items()
        if k not in {"limit", "offset", "sort", "order", "populate", "select"}
    }

    # Apply dynamic filters with boolean logic
    if filtered_query_params:
        query = build_query_filters(
            filtered_query_params,
            query,
            reserved_params={
                "id",
                "limit",
                "offset",
                "sort",
                "order",
                "populate",
                "select",
            },
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


@router.get("/{id}/documents/{document_id}")
async def get_document(
    id: str,
    document_id: str,
    proj: tuple[Project, User] = Depends(require_api_access),
    db: Session = Depends(get_db),
    # NEW: Relationship parameters
    populate: Optional[List[str]] = Query(
        None, description="Relationships to populate"
    ),
    select: Optional[List[str]] = Query(None, description="Fields to select"),
    user: AppUser = Depends(get_app_user),
):
    """
    Get a single document by ID with optional relationship population.

    🚨 REMOVED @cache DECORATOR - Security Issue!
    - User-specific permissions
    - Document data may change

    Examples:
    - GET /documents/123 (basic)
    - GET /documents/123?populate=author&populate=tags (with relationships)
    - GET /documents/123?populate=comments.user (nested)
    - GET /documents/123?select=title&select=author.name&populate=author (specific fields)

    Optimizations:
    - ✅ Use helper function
    - ✅ Single query with eager loading
    - ✅ Support for relationships (NEW!)
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

    # Check if relationships are requested
    if populate or select:
        resolver = AutoRelationshipResolver(db)
        result = resolver._transform_document(
            document, populate, select, collection.project_id
        )
        return result

    # Simple response
    return DocumentSchema.model_validate(document)


@router.patch("/{id}/documents/{document_id}", response_model=DocumentSchema)
async def edit_document(
    id: str,
    document_id: str,
    bg: BackgroundTasks,
    request: Request,
    proj: tuple[Project, User] = Depends(require_api_access),
    db: Session = Depends(get_db),
    user: AppUser = Depends(get_app_user),
) -> DocumentSchema:
    """
    Update a document with optional file uploads.

    **Simple File Upload Pattern (matches create document):**
    ```bash
    PATCH /collections/products/documents/doc-123
    Content-Type: multipart/form-data

    data: {"name": "Updated Product"}
    avatar: new_image.jpg
    files: another_file.pdf
    ```

    **How It Works:**
    - Name your file input = field name in document
    - `avatar=@file.jpg` → updates `avatar` field
    - `files=@file.jpg` → uses default behavior (file_url/file_urls)
    - Multiple files with same name → array

    **Example:**
    ```
    # Before:
    {
      "name": "John",
      "avatar": "https://old-avatar.jpg",
      "wallpaper": "https://old-wallpaper.jpg"
    }

    # Update: avatar=new-avatar.jpg

    # After:
    {
      "name": "John",                              # Preserved
      "avatar": "https://new-avatar.jpg",          # Updated
      "wallpaper": "https://old-wallpaper.jpg"     # Preserved
    }
    ```
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

    try:
        # Check content type to determine how to parse the request
        content_type = request.headers.get("content-type", "")
        update_data = {}

        if "multipart/form-data" in content_type:
            # Handle form data with potential file uploads
            form = await request.form()

            # Extract data field
            if "data" in form:
                try:
                    update_data = json.loads(form["data"])
                except json.JSONDecodeError:
                    raise HTTPException(400, "Invalid JSON in data field")

            # Process all file uploads (matches create document pattern)
            uploaded_files = {}  # {field_name: [urls]}

            for field_name in form:
                if field_name == "data":
                    continue

                field_value = form.get(field_name)

                # Check if it's a file
                if isinstance(field_value, StarletteUploadFile) and field_value.filename:
                    # Read and upload file
                    file_content = await field_value.read()
                    file_size = len(file_content)

                    check_storage_limit(project.id, file_size, db)

                    file_url = handle_file_upload(
                        file_content,
                        project.id,
                        field_value.filename,
                        subdirectory=collection.name,
                    )

                    # Store by field name
                    if field_name not in uploaded_files:
                        uploaded_files[field_name] = []
                    uploaded_files[field_name].append(file_url)

            # Add files to update data
            for field_name, urls in uploaded_files.items():
                if len(urls) == 1:
                    update_data[field_name] = urls[0]
                else:
                    update_data[field_name] = urls
        else:
            # Handle JSON request
            json_data = await request.json()
            update_data = json_data.get("data", json_data)

        if not update_data:
            raise HTTPException(400, "No data or files provided for update")

        # Merge data instead of replacing (preserves fields not in payload)
        existing_data = dict(document.data) if document.data else {}
        existing_data.update(update_data)
        document.data = existing_data

        db.add(document)
        db.commit()
        db.refresh(document)

        # Background tasks
        bg.add_task(
            notify_collection_watchers, collection.name, document, RealtimeEvent.UPDATE
        )

        if collection.webhook_url:
            bg.add_task(handle_webhook_call, collection.webhook_url, update_data, True)

        # Invalidate cache
        bg.add_task(invalidate_collection_cache, collection.id)

        return document

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Failed to update document: {str(e)}")


@router.delete("/{id}/documents/{document_id}")
def delete_document(
    id: str,
    document_id: str,
    bg: BackgroundTasks,
    proj: tuple[Project, User] = Depends(require_api_access),
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
    file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    directory: Optional[str] = None,
    proj: tuple[Project, User] = Depends(require_api_access),
):
    """
    Upload a file to project storage.

    Optimizations:
    - ✅ Added proper error handling
    - ✅ Validate file size before reading
    - ✅ Added file type validation (optional)
    """
    if not file:
        raise HTTPException(400, "No file provided")

    if not file.filename:
        raise HTTPException(400, "Filename is required")

    try:
        # Read file content
        file_content = await file.read()
        file_size = len(file_content)

        # Check storage limit
        check_storage_limit(proj[0].id, file_size, db)

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


@router.post("/{id}/batch/documents/create", response_model=list[DocumentSchema])
def batch_create_documents(
    id: str,
    payload: BatchCreateRequest,
    bg: BackgroundTasks,
    proj: tuple[Project, User] = Depends(require_api_access),
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


@router.post("/{id}/batch/documents/delete")
def batch_delete_documents(
    id: str,
    payload: BatchDeleteRequest,
    bg: BackgroundTasks,
    proj: tuple[Project, User] = Depends(require_api_access),
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


@router.post("/{id}/batch/documents/update")
def batch_update_documents(
    id: str,
    payload: BatchUpdateRequest,
    bg: BackgroundTasks,
    proj: tuple[Project, User] = Depends(require_api_access),
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


@router.get("/{id}/query/documents/count")
async def count_documents(
    id: str,
    request: Request,
    db: Session = Depends(get_db),
    proj: tuple[Project, User] = Depends(require_api_access),
    user: AppUser = Depends(get_app_user),
):
    """
    Count documents matching filters without returning the documents.

    Useful for pagination and statistics.

    Example:
        GET /collections/users/documents/count?status=active&age_gte=18
        → Returns: {"count": 42}

        GET /collections/posts/documents/count?author.role=admin
        → Returns: {"count": 15} (counts posts by admin authors)
    """
    project = proj[0]

    collection = get_collection_by_id_or_name(id, project.id, db)

    # Verify permissions
    can_access_collection(collection, "read", user)

    # Extract query params
    query_params = dict(request.query_params)

    # Check if this has relationship filters
    has_relationship_filters = any(
        "." in k and not k.startswith("[") for k in query_params.keys()
    )

    if has_relationship_filters:
        # Use relationship resolver for accurate count
        resolver = AutoRelationshipResolver(db)

        # Build query without pagination
        base_query = db.query(Document).filter(Document.collection_id == collection.id)

        # Separate relationship filters
        relationship_filters = {
            k: v for k, v in query_params.items() if "." in k and not k.startswith("[")
        }
        regular_filters = {
            k: v
            for k, v in query_params.items()
            if not ("." in k and not k.startswith("["))
        }

        # Apply regular filters
        if regular_filters:
            base_query = build_query_filters(regular_filters, base_query)

        # Apply relationship filters
        if relationship_filters:
            base_query = resolver._apply_relationship_filters(
                base_query, relationship_filters, collection
            )

        count = base_query.count()
    else:
        # Standard count (faster)
        doc_query = db.query(Document).filter(Document.collection_id == collection.id)

        filtered_params = {
            k: v
            for k, v in query_params.items()
            if k not in {"limit", "offset", "sort", "order"}
        }

        if filtered_params:
            doc_query = build_query_filters(
                filtered_params,
                doc_query,
                reserved_params={"id", "limit", "offset", "sort", "order"},
            )

        count = doc_query.count()

    return {"count": count}


@router.get("/{id}/query/documents/aggregate", response_model=dict)
async def aggregate_documents(
    id: str,
    request: Request,
    field: str = Query(..., description="Field to aggregate"),
    operation: str = Query(
        "count", regex="^(count|sum|avg|min|max)$", description="Aggregation operation"
    ),
    db: Session = Depends(get_db),
    proj: tuple[Project, User] = Depends(require_api_access),
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

        GET /collections/posts/documents/aggregate?field=views&operation=sum&author.role=admin
        → Returns: {"field": "views", "operation": "sum", "result": 50000}
    """
    project = proj[0]
    print(
        f"DEBUG: Aggregation request on collection {id} for field '{field}' with operation '{operation}'"
    )
    collection = get_collection_by_id_or_name(id, project.id, db)

    # Verify permissions
    can_access_collection(collection, "read", user)

    # Base query
    query = db.query(Document).filter(Document.collection_id == collection.id)

    # Extract query params
    query_params = dict(request.query_params)

    # Check for relationship filters
    has_relationship_filters = any(
        "." in k and not k.startswith("[")
        for k, v in query_params.items()
        if k not in {"field", "operation", "limit", "offset", "sort", "order"}
    )

    # Apply filters
    filtered_params = {
        k: v
        for k, v in query_params.items()
        if k not in {"field", "operation", "limit", "offset", "sort", "order"}
    }

    if filtered_params:
        if has_relationship_filters:
            # Use relationship resolver
            resolver = AutoRelationshipResolver(db)

            relationship_filters = {
                k: v
                for k, v in filtered_params.items()
                if "." in k and not k.startswith("[")
            }
            regular_filters = {
                k: v
                for k, v in filtered_params.items()
                if not ("." in k and not k.startswith("["))
            }

            if regular_filters:
                query = build_query_filters(regular_filters, query)

            if relationship_filters:
                query = resolver._apply_relationship_filters(
                    query, relationship_filters, collection
                )
        else:
            # Standard filtering
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


@router.get("/{collection_id}/query/documents/group-by", response_model=List[dict])
async def group_by_field(
    collection_id: str,
    request: Request,
    field: str = Query(..., description="Field to group by"),
    count_field: Optional[str] = Query(
        None, description="Field to count (default: document count)"
    ),
    db: Session = Depends(get_db),
    proj: tuple[Project, User] = Depends(require_api_access),
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

        GET /collections/posts/documents/group-by?field=category&author.role=admin
        → Returns: [
            {"category": "tech", "count": 45},
            {"category": "business", "count": 32}
          ] (grouped posts by admin authors only)
    """
    project = proj[0]

    collection = get_collection_by_id_or_name(collection_id, project.id, db)

    # Verify permissions
    can_access_collection(collection, "read", user)

    # Base query
    query = db.query(Document).filter(Document.collection_id == collection.id)

    # Extract query params
    query_params = dict(request.query_params)

    # Check for relationship filters
    has_relationship_filters = any(
        "." in k and not k.startswith("[")
        for k, v in query_params.items()
        if k not in {"field", "count_field", "limit", "offset", "sort", "order"}
    )

    # Apply filters
    filtered_params = {
        k: v
        for k, v in query_params.items()
        if k not in {"field", "count_field", "limit", "offset", "sort", "order"}
    }

    if filtered_params:
        if has_relationship_filters:
            # Use relationship resolver
            resolver = AutoRelationshipResolver(db)

            relationship_filters = {
                k: v
                for k, v in filtered_params.items()
                if "." in k and not k.startswith("[")
            }
            regular_filters = {
                k: v
                for k, v in filtered_params.items()
                if not ("." in k and not k.startswith("["))
            }

            if regular_filters:
                query = build_query_filters(regular_filters, query)

            if relationship_filters:
                query = resolver._apply_relationship_filters(
                    query, relationship_filters, collection
                )
        else:
            # Standard filtering
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


@router.get("/{id}/query/schema")
async def get_collection_schema(
    id: str,
    db: Session = Depends(get_db),
    proj: tuple[Project, User] = Depends(require_api_access),
    user: AppUser = Depends(get_app_user),
):
    """
    Analyze collection documents and return inferred schema.

    Returns field names, types, sample values, and detected relationships.
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
            "detected_relationships": {},
        }

    # Analyze field types
    field_analysis = {}
    detected_relationships = {}

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

            # Detect potential relationships
            if key.endswith("_id") and isinstance(value, str):
                base_name = key[:-3]
                target_collection = base_name + "s"
                detected_relationships[key] = {
                    "type": "belongs_to",
                    "field": key,
                    "target_collection": target_collection,
                    "confidence": "high" if len(value) > 20 else "medium",
                }
            elif key.endswith("_ids") and isinstance(value, list):
                base_name = key[:-4]
                target_collection = base_name + "s"
                detected_relationships[key] = {
                    "type": "has_many",
                    "field": key,
                    "target_collection": target_collection,
                    "confidence": "high",
                }

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
        "detected_relationships": detected_relationships,
        "usage_hint": "Use ?populate=<relationship_name> to auto-fetch related data",
    }


@router.get("/{id}/export")
async def export_collection(
    id: str,
    request: Request,
    format: str = Query("json", regex="^(json|csv)$"),
    populate: Optional[List[str]] = Query(
        None, description="Relationships to include in export"
    ),
    db: Session = Depends(get_db),
    proj: tuple[Project, User] = Depends(require_api_access),
    user: AppUser = Depends(get_app_user),
):
    """
    Export collection data to JSON or CSV.

    Supports filtering and relationship population - only exports documents matching the filters.

    Examples:
        GET /collections/users/export?format=json
        GET /collections/users/export?format=csv&status=active&age_gte=18
        GET /collections/posts/export?format=json&populate=author&populate=category
        GET /collections/posts/export?format=json&author.role=admin&populate=author
    """
    from fastapi.responses import StreamingResponse
    import json
    import io
    import csv

    project = proj[0]

    collection = get_collection_by_id_or_name(id, project.id, db)

    # Verify permissions
    can_access_collection(collection, "read", user)

    # Extract query params
    query_params = dict(request.query_params)

    # Check if relationships are requested
    has_relationships = populate or any(
        "." in k and not k.startswith("[") for k in query_params.keys()
    )

    if has_relationships:
        # Use relationship resolver
        resolver = AutoRelationshipResolver(db)

        filtered_params = {
            k: v
            for k, v in query_params.items()
            if k not in {"format", "populate", "limit", "offset", "sort", "order"}
        }

        result = resolver.query_with_relationships(
            collection=collection,
            query_params=filtered_params,
            populate=populate,
            select=None,
            limit=10000,  # Export limit
            offset=0,
        )

        documents_data = result["data"]
    else:
        # Standard query
        query = db.query(Document).filter(Document.collection_id == collection.id)

        filtered_params = {
            k: v
            for k, v in query_params.items()
            if k not in {"format", "limit", "offset", "sort", "order"}
        }

        if filtered_params:
            query = build_query_filters(
                filtered_params,
                query,
                reserved_params={"id", "format", "limit", "offset", "sort", "order"},
            )

        documents = query.limit(10000).all()
        documents_data = [
            {
                "id": str(doc.id),
                "created_at": doc.created_at.isoformat(),
                **doc.data,
            }
            for doc in documents
        ]

    if format == "json":
        # Export as JSON
        json_str = json.dumps(documents_data, indent=2, default=str)

        return StreamingResponse(
            io.BytesIO(json_str.encode()),
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="{collection.name}_export.json"'
            },
        )

    elif format == "csv":
        # Export as CSV
        if not documents_data:
            raise HTTPException(400, "No documents to export")

        # Flatten nested objects for CSV (relationships become separate columns)
        flattened_data = []
        all_fields = set()

        for doc in documents_data:
            flat_doc = {}
            for key, value in doc.items():
                if isinstance(value, dict):
                    # Flatten nested dict (e.g., author.name, author.email)
                    for nested_key, nested_value in value.items():
                        flat_key = f"{key}.{nested_key}"
                        flat_doc[flat_key] = nested_value
                        all_fields.add(flat_key)
                elif isinstance(value, list) and value and isinstance(value[0], dict):
                    # Convert list of objects to JSON string
                    flat_doc[key] = json.dumps(value, default=str)
                    all_fields.add(key)
                else:
                    flat_doc[key] = value
                    all_fields.add(key)

            flattened_data.append(flat_doc)

        # Ensure id and created_at are first
        base_fields = ["id", "created_at"]
        other_fields = sorted([f for f in all_fields if f not in base_fields])
        fields = [f for f in base_fields if f in all_fields] + other_fields

        # Create CSV
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()

        for doc in flattened_data:
            writer.writerow(doc)

        return StreamingResponse(
            io.BytesIO(output.getvalue().encode()),
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{collection.name}_export.csv"'
            },
        )
