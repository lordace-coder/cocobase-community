from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.auth_collection import AppUserSchema
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.middleware import track_api_call
from app.models.collections import Collection, Document
from app.models.user import User
from app.models.app_client import Project, AppUser
from app.schemas.collections import CollectionSchema, DocumentCreateSchema
from app.schemas.projects import ProjectInDBBase, ProjectCreate, ProjectUpdate
from app.schemas.collections import DocumentSchema
from app.services.utils import generate_api_key
from app.websockets.documents import RealtimeEvent, notify_collection_watchers

router = APIRouter(
    prefix="/project",
    dependencies=[Depends(get_current_user), Depends(track_api_call)],
    tags=["Project"],
)


@router.get("/")
def get_all_projects(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[ProjectInDBBase]:
    projects = db.query(Project).filter(Project.user_id == user.id)
    return projects


@router.post("/")
def create_project(
    payload: ProjectCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectInDBBase:
    # check if project name exists
    if (
        db.query(Project)
        .filter(Project.name == payload.name, Project.owner == user)
        .count()
    ):
        raise HTTPException(400, "Project with this name already exists")
    proj = Project(**payload.model_dump(), owner=user)
    proj.api_key = generate_api_key()
    db.add(proj)
    db.commit()
    db.refresh(proj)
    return proj


@router.delete("/{id}")
def delete_project(
    id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    try:
        db.query(Project).filter(Project.id == id, Project.user_id == user.id).delete()
        db.commit()
        return
    except Exception as e:
        raise HTTPException(400, "Error occured " + str(e))


@router.get("/{id}")
def get_project(
    id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> ProjectInDBBase:
    try:
        x = (
            db.query(Project)
            .filter(Project.id == id, Project.user_id == user.id)
            .first()
        )
        return x
    except Exception as e:
        raise HTTPException(400, "Error occured " + str(e))


@router.get("/regen-api-key/{projectId}", response_model=ProjectInDBBase)
def generate_new_api_key(
    projectId: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = (
        db.query(Project)
        .filter(Project.id == projectId, Project.user_id == user.id)
        .first()
    )
    project.api_key = generate_api_key()
    db.add(project)
    db.commit()
    return project


@router.patch("/{id}")
def update_project(
    id: str,
    payload: ProjectUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectInDBBase:
    project = (
        db.query(Project).filter(Project.id == id, Project.user_id == user.id).first()
    )
    update_data = payload.dict(exclude_unset=True)

    for key, val in update_data.items():
        setattr(project, key, val)

    db.add(project)
    db.commit()
    db.refresh(project)
    return project


# get collections in a project
@router.get("/{id}/collections")
def get_collections_in_project(
    id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[CollectionSchema]:
    from app.schemas.collections import CollectionSchema

    project = (
        db.query(Project).filter(Project.id == id, Project.user_id == user.id).first()
    )
    if not project:
        raise HTTPException(404, "Project not found")

    return project.collections


# get collection by id
@router.get("/{id}/collections/{collection_id}")
def get_collection_by_id(
    id: str,
    collection_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CollectionSchema:

    project = (
        db.query(Project).filter(Project.id == id, Project.user_id == user.id).first()
    )
    if not project:
        raise HTTPException(404, "Project not found")

    collection = (
        db.query(Collection)
        .filter(Collection.id == collection_id, Collection.project_id == project.id)
        .first()
    )
    if not collection:
        raise HTTPException(404, "Collection not found")

    return collection


# get documents in a collection
@router.get("/{id}/collections/{collection_id}/documents")
def get_documents_in_collection(
    id: str,
    collection_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[DocumentSchema]:

    project = (
        db.query(Project).filter(Project.id == id, Project.user_id == user.id).first()
    )
    if not project:
        raise HTTPException(404, "Project not found")

    collection = (
        db.query(Collection)
        .filter(Collection.id == collection_id, Collection.project_id == project.id)
        .first()
    )
    if not collection:
        raise HTTPException(404, "Collection not found")

    return collection.documents


# create a new document in a project
@router.post(
    "/{id}/collections/{collection_id}/documents", response_model=DocumentSchema
)
def create_document_in_collection(
    id: str,
    bg: BackgroundTasks,
    collection_id: str,
    payload: DocumentCreateSchema,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DocumentSchema:

    project = (
        db.query(Project).filter(Project.id == id, Project.user_id == user.id).first()
    )
    if not project:
        raise HTTPException(404, "Project not found")

    collection = (
        db.query(Collection)
        .filter(Collection.id == collection_id, Collection.project_id == project.id)
        .first()
    )
    if not collection:
        raise HTTPException(404, "Collection not found")

    document = Document(**payload.model_dump(), collection_id=collection.id)

    db.add(document)
    db.commit()
    db.refresh(document)
    bg.add_task(
        notify_collection_watchers, collection.id, document, RealtimeEvent.create
    )
    return document


# delete a document in a collection
@router.delete("/{id}/collections/{collection_id}/documents/{document_id}")
def delete_document_in_collection(
    id: str,
    collection_id: str,
    document_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = (
        db.query(Project).filter(Project.id == id, Project.user_id == user.id).first()
    )
    if not project:
        raise HTTPException(404, "Project not found")

    collection = (
        db.query(Collection)
        .filter(Collection.id == collection_id, Collection.project_id == project.id)
        .first()
    )
    if not collection:
        raise HTTPException(404, "Collection not found")

    result = (
        db.query(Document)
        .filter(
            Document.id == document_id,
            Document.collection_id == collection.id,
        )
        .delete()
    )

    if not result:
        raise HTTPException(404, "Document not found")

    db.commit()
    return {"message": "Document deleted successfully"}


# update a document in a collection
@router.patch("/{id}/collections/{collection_id}/documents/{document_id}")
def update_document_in_collection(
    id: str,
    collection_id: str,
    document_id: str,
    bg: BackgroundTasks,
    payload: DocumentCreateSchema,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DocumentSchema:

    project = (
        db.query(Project).filter(Project.id == id, Project.user_id == user.id).first()
    )
    if not project:
        raise HTTPException(404, "Project not found")

    collection = (
        db.query(Collection)
        .filter(Collection.id == collection_id, Collection.project_id == project.id)
        .first()
    )
    if not collection:
        raise HTTPException(404, "Collection not found")

    document = (
        db.query(Document)
        .filter(Document.id == document_id, Document.collection_id == collection.id)
        .first()
    )
    if not document:
        raise HTTPException(404, "Document not found")
    if not payload.data:
        raise HTTPException(400, "No data provided to update")

    # For JSONB columns, we need to assign the new data directly
    _data = dict(document.data) if document.data else {}

    _data.update(payload.data)
    document.data = _data

    db.add(document)
    db.commit()
    db.refresh(document)
    bg.add_task(
        notify_collection_watchers, collection.id, document, RealtimeEvent.update
    )
    return document


# project users


# list users
@router.get("/{id}/users")
def list_users(
    id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[AppUserSchema]:
    proj = (
        db.query(Project).filter(Project.id == id, Project.user_id == user.id).first()
    )
    users = db.query(AppUser).filter(AppUser.client_id == proj.id)
    return users


# get user by id
@router.get("/{id}/users/{userid}")
def get_user(
    id: str,
    userid: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[AppUserSchema]:
    proj = (
        db.query(Project).filter(Project.id == id, Project.user_id == user.id).first()
    )
    user = db.query(AppUser).filter(AppUser.client_id == userid).first()
    return user
