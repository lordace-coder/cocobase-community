from datetime import datetime
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
from app.core.database import get_db
from app.core.dependencies import get_app_user, get_project
from app.core.middleware import track_api_call
from app.core.permissions import can_access_collection
from app.models.app_client import Project
from app.models.user import User
from sqlalchemy.orm import Session
from app.models.collections import Document, Collection
from app.schemas.collections import *
from sqlalchemy import cast, Integer, String
from fastapi.encoders import jsonable_encoder

from app.services.utils import handle_webhook_call
from app.storage.storage import check_storage_limit, handle_file_upload
from app.websockets.documents import RealtimeEvent, notify_collection_watchers
from fastapi_cache.decorator import cache
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend

router = APIRouter(
    prefix="/collections",
    tags=["Collections"],
    dependencies=[Depends(get_project), Depends(track_api_call)],
)
comparison_map = {
    "lte": lambda col, val: cast(col.astext, Integer) <= val,
    "gte": lambda col, val: cast(col.astext, Integer) >= val,
    "lt": lambda col, val: cast(col.astext, Integer) < val,
    "gt": lambda col, val: cast(col.astext, Integer) > val,
    "eq": lambda col, val: col.astext == str(val),
    "contains": lambda col, val: col.astext.ilike(f"%{val}%"),
}


@router.post("/", status_code=201, response_model=CollectionSchema)
def create_collection(
    payload: CollectionCreateSchema,
    db: Session = Depends(get_db),
    proj: tuple[Project, User] = Depends(get_project),
):
    project, _ = proj

    # check if collection with this name already exist in the project
    query = (
        db.query(Collection)
        .filter(Collection.project_id == project.id, payload.name == Collection.name)
        .first()
    )
    if query:
        raise HTTPException(
            400, "You cant have two collections with the same name on a project"
        )

    new_collection = Collection(
        **payload.model_dump(),
        project_id=project.id,
        project=project,
    )

    db.add(new_collection)
    db.commit()
    # update connections

    db.refresh(new_collection)
    return new_collection


@router.patch("/{collection_id}", response_model=CollectionSchema)
def update_collection(
    collection_id: str,
    payload: CollectionUpdateSchema,
    db: Session = Depends(get_db),
    proj: tuple[Project, User] = Depends(get_project),
):
    project, _ = proj

    # Get the collection and verify it exists and belongs to the project
    collection = (
        db.query(Collection)
        .filter(Collection.id == collection_id, Collection.project_id == project.id)
        .first()
    )

    if not collection:
        raise HTTPException(
            status_code=404,
            detail="Collection not found or doesn't belong to this project",
        )

    # Check if new name conflicts with existing collections
    if payload.name:
        existing = (
            db.query(Collection)
            .filter(
                Collection.project_id == project.id,
                Collection.name == payload.name,
                Collection.id != collection_id,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=400,
                detail="A collection with this name already exists in the project",
            )
        collection.name = payload.name

    db.add(collection)
    db.commit()
    db.refresh(collection)
    return collection


@router.delete("/{collection_id}", status_code=204)
def delete_collection(
    collection_id: str,
    db: Session = Depends(get_db),
    proj: tuple[Project, User] = Depends(get_project),
):
    project, _ = proj

    # Delete the collection if it exists and belongs to the project
    result = (
        db.query(Collection)
        .filter(Collection.id == collection_id, Collection.project_id == project.id)
        .delete()
    )

    if not result:
        raise HTTPException(
            status_code=404,
            detail="Collection not found or doesn't belong to this project",
        )

    db.commit()
    return None


# * FOR DOCUMENTS
@router.post("/documents")
def create_new_document(
    payload: DocumentCreateSchema,
    bg: BackgroundTasks,
    collection: str | None = None,
    db: Session = Depends(get_db),
    proj: tuple[Project, User] = Depends(get_project),
    user: AppUser = Depends(get_app_user),
) -> DocumentSchema:
    project, _ = proj

    if not collection:
        raise HTTPException(400, "Collection name or id is required")

    if not payload.data:
        raise HTTPException(400, "Document data is required")

    # First try to find existing collection
    _collection = (
        db.query(Collection)
        .filter(
            ((Collection.id == collection) | (Collection.name == collection)),
            Collection.project_id == project.id,
        )
        .first()
    )

    # If no collection exists, create a new one
    if not _collection:
        _collection = Collection(
            name=collection,  # Use the collection parameter as the name
            project_id=project.id,
            project=project,
        )
        db.add(_collection)
        db.commit()
        db.refresh(_collection)
    # *VERIFY APPUSER HAS REQUIRED PERMISSIONS
    can_access_collection(_collection, "create", user)
    try:
        # Create and attach the document to the collection
        new_doc = Document(
            data=payload.data,
            collection_id=_collection.id,
        )
        db.add(new_doc)
        db.commit()
        db.refresh(new_doc)
        bg.add_task(handle_webhook_call, _collection.webhook_url, payload.data)
        bg.add_task(
            notify_collection_watchers, _collection.id, new_doc, RealtimeEvent.create
        )
        return new_doc
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Failed to create document: {str(e)}")


@router.get("/{id}/documents")
@cache(expire=60)  # cache for 60 seconds
async def list_documents(
    id: str,
    request: Request,
    db: Session = Depends(get_db),
    proj: tuple[Project, User] = Depends(get_project),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    user: AppUser = Depends(get_app_user),
) -> list[DocumentSchema]:
    project = proj[0]

    collection = (
        db.query(Collection)
        .filter(
            (Collection.id == id) | (Collection.name == id),
            Collection.project_id == project.id,
        )
        .first()
    )
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    # *VERIFY APPUSER HAS REQUIRED PERMISSIONS
    can_access_collection(collection, "read", user)
    query = db.query(Document).filter(Document.collection_id == collection.id)

    for key, value in request.query_params.items():
        if key in ["id", "limit", "offset"]:  # skip reserved
            continue

        if "_" in key:
            field, op = key.rsplit("_", 1)
        else:
            field, op = key, "eq"

        json_col = Document.data[field]
        comp_fn = comparison_map.get(op)
        if comp_fn:
            try:
                value = int(value) if op in {"lte", "gte", "lt", "gt"} else value
                query = query.filter(comp_fn(json_col, value))
            except ValueError:
                continue

    results = query.offset(offset).limit(limit).all()
    return results


@router.delete("/{id}/documents/{document_id}")
def delete_document(
    id: str,
    document_id: str,
    proj: tuple[Project, User] = Depends(get_project),
    db: Session = Depends(get_db),
    user: AppUser = Depends(get_app_user),
):
    project = proj[0]
    # First verify collection exists and belongs to project
    collection = (
        db.query(Collection)
        .filter(
            ((Collection.id == id) | (Collection.name == id)),
            Collection.project_id == project.id,
        )
        .first()
    )
    if not collection:
        raise HTTPException(
            status_code=404,
            detail="Collection not found or doesn't belong to this project",
        )
    # *VERIFY APPUSER HAS REQUIRED PERMISSIONS
    can_access_collection(collection, "delete", user)
    try:
        result = (
            db.query(Document)
            .filter(Document.id == document_id, Document.collection_id == collection.id)
            .delete()
        )
        if not result:
            raise HTTPException(404, "Document not found in this collection")
        db.commit()
        return {"status": "success", "message": "Document deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Failed to delete document: {str(e)}")


@router.get("/{id}/documents/{document_id}")
@cache(expire=60)
async def get_document(
    id: str,
    document_id: str,
    proj: tuple[Project, User] = Depends(get_project),
    db: Session = Depends(get_db),
    user: AppUser = Depends(get_app_user),
) -> DocumentSchema:
    project = proj[0]
    # First verify collection exists and belongs to project
    collection = (
        db.query(Collection)
        .filter(
            ((Collection.id == id) | (Collection.name == id)),
            Collection.project_id == project.id,
        )
        .first()
    )
    if not collection:
        raise HTTPException(
            status_code=404,
            detail="Collection not found or doesn't belong to this project",
        )
    # *VERIFY APPUSER HAS REQUIRED PERMISSIONS
    can_access_collection(collection, "read", user)
    document = (
        db.query(Document)
        .filter(Document.id == document_id, Document.collection_id == collection.id)
        .first()
    )
    if not document:
        raise HTTPException(404, "Document not found in this collection")

    return document


# update a document
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
    project = proj[0]

    # Verify collection exists and belongs to project
    collection = (
        db.query(Collection)
        .filter(
            (Collection.id == id) | (Collection.name == id),
            Collection.project_id == project.id,
        )
        .first()
    )

    if not collection:
        raise HTTPException(
            status_code=404,
            detail="Collection not found or doesn't belong to this project",
        )
    # *VERIFY APPUSER HAS REQUIRED PERMISSIONS
    can_access_collection(collection, "update", user)
    # Get and verify document exists
    document = (
        db.query(Document)
        .filter(Document.id == document_id, Document.collection_id == collection.id)
        .first()
    )

    if not document:
        raise HTTPException(
            status_code=404, detail="Document not found in this collection"
        )

    # Update document data
    document.data = payload.data

    db.add(document)
    db.commit()
    db.refresh(document)
    bg.add_task(
        notify_collection_watchers, collection.id, document, RealtimeEvent.update
    )
    bg.add_task(handle_webhook_call, collection.webhook_url, payload.data, True)
    return document


@router.post("/file")
async def upload_file_to_project(
    file: UploadFile,
    directory: str = None,
    proj: tuple[Project, User] = Depends(get_project),
):
    filename = file.filename
    file_content = await file.read()  # Read the content into memory
    file_size = len(file_content)

    check_storage_limit(proj[0].id, file_size)

    # Pass the content and filename to the handler
    try:
        res = handle_file_upload(file_content, proj[0].id, filename, directory)
        return {"message": "File uploaded successfully", "url": res}
    except Exception as e:
        return {"error": str(e)}, 500
