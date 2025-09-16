from fastapi import APIRouter,HTTPException

from app.storage.storage import get_files
# TODO IMPLEMEN FILE UPLOAD HERE AS WELL AS DELETE
# TODO IMPLEMENT FILE UPLOAD INSIDE THE COLLECTION FOR THE CLIENT

router = APIRouter(prefix="/storage",tags=['Storage'])



@router.get("/files/{project_id}")
def get_project_files(project_id:str):
    return get_files(project_id)