from datetime import date
import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.collections import Collection, Document
from app.models.hits import RouteHit
from app.models.user import User
from app.models.app_client import Project, AppUser
from app.models.timeline import Suggestion, SuggestionLike
from app.schemas.collections import CollectionSchema, DocumentCreateSchema
from app.schemas.files import UploadedFileSchema
from app.schemas.projects import ProjectInDBBase, ProjectCreate, ProjectUpdate
from app.schemas.collections import DocumentSchema
from app.schemas.suggestions import SuggestionCreate, SuggestionSchema
from app.services.cloudinary import delete_file
from app.services.utils import generate_api_key


router = APIRouter(tags=["API"], prefix="/api")

