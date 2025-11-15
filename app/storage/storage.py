from fastapi import HTTPException
from fastapi.responses import StreamingResponse
import boto3
import aioboto3
from botocore.exceptions import ClientError
import os
from typing import Dict
import io

from app.models.pricing import get_current_plan
from app.services.notification import send_notification_to_project_users


# B2 Configuration
B2_KEY_ID = os.getenv("BACKBLAZE_KEY_ID")
B2_APPLICATION_KEY = os.getenv("BACKBLAZE_APPLICATION_KEY")
B2_ENDPOINT = os.getenv("BUCKET_ENDPOINT")
B2_BUCKET = os.getenv("BUCKET_NAME")
# Storage limit per project (50MB in bytes)

PUBLIC_BASE_URL = f"https://f005.backblazeb2.com/file/{B2_BUCKET}/"

# Initialize B2 client (synchronous - for backwards compatibility)
s3_client = boto3.client(
    "s3",
    endpoint_url=B2_ENDPOINT,
    aws_access_key_id=B2_KEY_ID,
    aws_secret_access_key=B2_APPLICATION_KEY,
)

# Initialize async session for S3 operations (OPTIMIZED)
aioboto3_session = aioboto3.Session()


def get_project_usage(project_id: str) -> int:
    """
    Get current storage usage for a project in bytes.

    DEPRECATED: This still lists all files. Use get_cached_project_usage() instead.
    Kept for backwards compatibility.
    """
    try:
        response = s3_client.list_objects_v2(
            Bucket=B2_BUCKET, Prefix=f"projects/{project_id}/"
        )

        total_size = 0
        if "Contents" in response:
            for obj in response["Contents"]:
                total_size += obj["Size"]

        return total_size
    except ClientError:
        return 0


def get_cached_project_usage(project_id: str, db) -> int:
    """
    Get cached storage usage for a project in bytes.

    OPTIMIZED: Uses database cache instead of listing all S3 files.
    Much faster than get_project_usage().
    """
    from app.models.app_client import Project

    project = db.query(Project).filter(Project.id == project_id).first()
    if project and project.storage_used_bytes is not None:
        return project.storage_used_bytes
    return 0


def update_project_storage_cache(project_id: str, file_size_delta: int, db):
    """
    Update the cached storage usage for a project.

    OPTIMIZED: Incremental update instead of recalculating from S3.

    :param project_id: The project ID
    :param file_size_delta: The change in bytes (positive for upload, negative for delete)
    :param db: Database session
    """
    from app.models.app_client import Project
    from datetime import datetime

    project = db.query(Project).filter(Project.id == project_id).first()
    if project:
        current_usage = project.storage_used_bytes or 0
        project.storage_used_bytes = max(0, current_usage + file_size_delta)
        project.storage_last_updated = datetime.utcnow()
        db.commit()


def check_storage_limit(project_id: str, file_size: int, db):
    """
    Check if uploading a file would exceed storage limit.

    OPTIMIZED: Uses cached storage value instead of listing all files.
    """
    STORAGE_LIMIT_PER_PROJECT = get_current_plan(db=db, project=project_id).max_storage_mb * 1024 * 1024
    current_usage = get_cached_project_usage(project_id, db)

    if current_usage + file_size > STORAGE_LIMIT_PER_PROJECT:
        send_notification_to_project_users(
            project_id,
            "You have reached the storage limit for your current plan, kindly purchase a higher plan and try again.",
        )
        raise HTTPException(
            status_code=413,
            detail=f"Storage limit exceeded. Current: {current_usage/1024/1024:.2f}MB, "
            f"Limit: {STORAGE_LIMIT_PER_PROJECT/1024/1024}MB",
        )


def get_files(project_id: str, subdirectory: str | None):
    prefix = f"projects/{project_id}/"
    if subdirectory != None:
        prefix += f"{subdirectory}"

    response = s3_client.list_objects_v2(Bucket=B2_BUCKET, Prefix=prefix)

    files = []
    if "Contents" in response:
        for obj in response["Contents"]:

            key = obj["Key"]
            filename = key.replace(prefix, "")

            if (
                not filename or ".bzEmpty" in filename
            ):  # skip empty "directory" placeholders
                continue

            file_info = {
                "filename": filename,
                "url": f"{PUBLIC_BASE_URL}{key}",  # short permanent public link
                "size": obj["Size"],  # in bytes
                "last_modified": obj["LastModified"].isoformat(),
                "etag": obj["ETag"].strip('"'),
            }
            files.append(file_info)

    return files


async def handle_file_upload(
    file_content: bytes, project_id: str, filename: str, subdirectory: str | None, db=None
):
    """
    Uploads a file's content to a B2 bucket using S3-compatible aioboto3.

    OPTIMIZED: Async upload to prevent blocking the request + updates storage cache.

    :param file_content: The binary content of the file.
    :param project_id: The project ID for the S3-like path.
    :param filename: The name of the file.
    :param subdirectory: Optional subdirectory within the project folder.
    :param db: Database session for updating storage cache.
    :return: The public URL of the uploaded file.
    """
    # Create a file-like object from the in-memory bytes
    file_obj = io.BytesIO(file_content)
    file_size = len(file_content)

    # Construct the object key (S3-style path)
    s3_object_key = f"projects/{project_id}"
    if subdirectory != None:
        s3_object_key += f"/{subdirectory}"
    s3_object_key += f"/{filename}"

    # Use async upload_fileobj
    try:
        async with aioboto3_session.client(
            "s3",
            endpoint_url=B2_ENDPOINT,
            aws_access_key_id=B2_KEY_ID,
            aws_secret_access_key=B2_APPLICATION_KEY,
        ) as s3:
            await s3.upload_fileobj(file_obj, B2_BUCKET, s3_object_key)
            print(f"✅ Successfully uploaded '{filename}' to S3 at '{s3_object_key}'")

            # Update storage cache (OPTIMIZED)
            if db:
                update_project_storage_cache(project_id, file_size, db)

            return PUBLIC_BASE_URL + s3_object_key
    except Exception as e:
        print(f"❌ An error occurred during upload: {e}")
        # Re-raise the exception or handle it as needed
        raise


def delete_s3_file(object_key):
    """
    Deletes a single object from an S3 bucket.

    :param bucket_name: Name of the S3 bucket.
    :param object_key: The S3 object key (path to the file).
    :return: True if the object was deleted, False otherwise.
    """
    try:
        s3_client.delete_object(Bucket=B2_BUCKET, Key=object_key)
        print(f"✅ Successfully deleted {object_key} from {B2_BUCKET}")
        return True
    except Exception as e:
        print(f"❌ An error occurred: {e}")
        return False
