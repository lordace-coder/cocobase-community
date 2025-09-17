from fastapi import APIRouter, HTTPException, Response, UploadFile
from fastapi.responses import JSONResponse
from app.schemas.storage import FilesSchema
from app.storage.storage import (
    check_storage_limit,
    delete_s3_file,
    get_files,
    handle_file_upload,
)

# TODO IMPLEMEN FILE UPLOAD HERE AS WELL AS DELETE
# TODO IMPLEMENT FILE UPLOAD INSIDE THE COLLECTION FOR THE CLIENT

router = APIRouter(prefix="/storage", tags=["Storage"])


@router.get("/files/{project_id}", response_model=list[FilesSchema])
def get_project_files(
    project_id: str,
):
    # TODO VERIFY USER HAS ACCESS TO THIS PROJECT
    return get_files(project_id)


@router.delete("/files/{project_id}/{object_key}")
def delete_project_files(project_id: str, filename: str):
    key = f"projects/{project_id}/{filename}"
    if delete_s3_file(key):
        return JSONResponse(status_code=200, content={})
    return JSONResponse(status_code=400, content={})


@router.post("/files/{project_id}")
async def upload_project_file(project_id: str, file: UploadFile):
    filename = file.filename
    file_content = await file.read()  # Read the content into memory
    file_size = len(file_content)

    check_storage_limit(project_id, file_size)

    # Pass the content and filename to the handler
    try:
        res = handle_file_upload(file_content, project_id, filename)
        return {"message": "File uploaded successfully", "s3_response": str(res)}
    except Exception as e:
        return {"error": str(e)}, 500


@router.get("/storage-info/{project_id}")
def get_project_storage_info(project_id:str):
    return {
        "total_storage":None,
        "available":None
    }