import enum
from fastapi import APIRouter, HTTPException, Response, UploadFile
from fastapi.params import Depends
from fastapi.responses import JSONResponse
from app.core.database import get_db
from app.models.pricing import PricingPlan
from sqlalchemy.orm import Session
from app.models.app_client import Project
from app.schemas.storage import FilesSchema
from app.storage.storage import (
    check_storage_limit,
    delete_s3_file,
    get_files,
    handle_file_upload,
    get_project_usage,
)

# TODO IMPLEMEN FILE UPLOAD HERE AS WELL AS DELETE
# TODO IMPLEMENT FILE UPLOAD INSIDE THE COLLECTION FOR THE CLIENT

router = APIRouter(prefix="/storage", tags=["Storage"])


class DefaultDirectories:
    templates = "__templates__"
    static = "__static__"
    files = "media"


@router.get("/files/{project_id}", response_model=list[FilesSchema])
def get_project_files(
    project_id: str,
    directory: str = None,
):
    # TODO VERIFY USER HAS ACCESS TO THIS PROJECT
    return get_files(project_id, directory)


@router.delete("/files/{project_id}/{object_key}")
def delete_project_files(project_id: str, filename: str, directory: str = None):
    key = f"projects/{project_id}"
    if directory != None:
        key += f"/{directory}"

    key += f"/{filename}"
    if delete_s3_file(key):
        return JSONResponse(status_code=200, content={})
    return JSONResponse(status_code=400, content={})


@router.post("/files/{project_id}")
async def upload_project_file(
    project_id: str,
    file: UploadFile,
    directory: str = None,
):
    filename = file.filename.replace(" ", "_")  # Sanitize filename
    file_content = await file.read()  # Read the content into memory
    file_size = len(file_content)

    check_storage_limit(project_id, file_size)

    # Pass the content and filename to the handler
    try:
        res = handle_file_upload(file_content, project_id, filename, directory)
        return {"message": "File uploaded successfully", "s3_response": str(res)}
    except Exception as e:
        return {"error": str(e)}, 500


@router.get("/storage-info/{project_id}")
def get_project_storage_info(project_id: str, db: Session = Depends(get_db)):
    proj_usage = get_project_usage(project_id)
    default_plan: PricingPlan = db.query(PricingPlan).get(1)
    project: Project = db.query(Project).get(project_id)
    if project and project.subscriptions:
        active_sub = next((sub for sub in project.subscriptions if sub.is_active), None)
        if active_sub and active_sub.plan:
            plan = active_sub.plan
            total_storage = plan.max_storage_mb * 1024 * 1024  # Convert MB to bytes
            available_storage = total_storage - proj_usage
            return {
                "total_storage": total_storage,
                "available": available_storage,
                "used": proj_usage,
            }
    total_storage = default_plan.max_storage_mb * 1024 * 1024  # Convert MB to bytes
    available_storage = total_storage - proj_usage
    return {
        "total_storage": total_storage,
        "available": available_storage,
        "used": proj_usage,
    }
