from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.core.database import get_db
from app.core.dependencies import get_project
from app.models.app_client import Project
from app.models.user import User
from sqlalchemy.orm import Session
from app.models.collections import Document, Collection


router = APIRouter(
    prefix="/client",
    dependencies=[Depends(get_project)],
)


class CollectionCreate(BaseModel):
    name: str


@router.post("/collection", status_code=201)
def create_collection(
    payload: CollectionCreate,
    db: Session = Depends(get_db),
    proj: tuple[Project, User] = Depends(get_project),
):
    project, owner = proj

    # check if collection with this name already exisit in the project
    query = db.query(Collection).filter(
        Collection.project_id == project.id, payload.name == Collection.name
    )
    if query:
        raise HTTPException(
            400, "You cant have two collections with the same name on a project"
        )
    
    new_collection = Collection(
        
    )

    db.add(new_collection)
    db.commit()
    db.refresh(new_collection)
    return new_collection
