
from fastapi import UploadFile
from app.storage.storage import check_storage_limit,s3_client

# TODO CREATE FUNCTION FOR LISTING  FILES IN A PROJECT
# TODO CREATE FUNC FOR DELETING FILES AND FORMATING PROJECT STORAGE

async def upload_file_to_project(project_id :str,file:UploadFile):
    file_content = await file.read()
    file_size = len(file_content)
    check_storage_limit(project_id,file_size)
    object_key = f"projects/{project_id}/{file.filename}"

    s3_client.upload_file()