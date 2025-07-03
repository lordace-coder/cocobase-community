from fastapi import APIRouter, UploadFile, File, HTTPException, status, Depends
from app.schemas.files import FileResponse
from app.core.dependencies import get_project, get_db
from app.models.user import User
from app.models.app_client import Project
from app.services.cloudinary import upload
from sqlalchemy.orm import Session
from app.models.files import FileType, UploadedFile, UserStorage

router = APIRouter(prefix="/files", tags=["Files Manager"])
MAX_FILE_SIZE = 5 * 1024 * 1024


@router.post("/upload-file", response_model=FileResponse)
async def handle_file_upload(

    db: Session = Depends(get_db),
    file: UploadFile = File(...),
    project: tuple[Project, User] = Depends(get_project),
):
    user = project[1]

    # Check file size before upload
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)

    # Get or create UserStorage
    storage = db.query(UserStorage).filter(UserStorage.user_id == user.id).first()
    if not storage:
        storage = UserStorage(user_id=user.id)
        db.add(storage)
        db.flush()

    if storage.used_storage + size > storage.max_storage:
        raise HTTPException(
            status_code=413,
            detail="Storage limit exceeded Go to project to reduce files",
        )

    # Upload to Cloudinary
    try:
        result = upload(
            file.file,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cloudinary error: {str(e)}")

    # Save file record
    uploaded_file = UploadedFile(
        user_id=user.id,
        url=result.url,
        public_id=result.public_id,
        format=result.format,
        file_type=FileType(result.type),
        size=size,
    )
    db.add(uploaded_file)

    # Update user storage
    storage.used_storage += size
    db.commit()

    return FileResponse(
        url=result.url,
    )


