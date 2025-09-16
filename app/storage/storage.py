from fastapi import HTTPException
from fastapi.responses import StreamingResponse
import boto3
from botocore.exceptions import ClientError
import os
from typing import Dict
import io


# B2 Configuration
B2_KEY_ID = os.getenv("BACKBLAZE_KEY_ID")
B2_APPLICATION_KEY = os.getenv("BACKBLAZE_APPLICATION_KEY")
B2_ENDPOINT = os.getenv("BUCKET_ENDPOINT")
B2_BUCKET = os.getenv("BUCKET_NAME")
PUBLIC_BASE_URL = f"https://f004.backblazeb2.com/file/{B2_BUCKET}/"
# Storage limit per project (50MB in bytes)
STORAGE_LIMIT_PER_PROJECT = 50 * 1024 * 1024  # 50MB

# Initialize B2 client
s3_client = boto3.client(
    "s3",
    endpoint_url=B2_ENDPOINT,
    aws_access_key_id=B2_KEY_ID,
    aws_secret_access_key=B2_APPLICATION_KEY,
)


def get_project_usage(project_id: str) -> int:
    """Get current storage usage for a project in bytes"""
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


def check_storage_limit(project_id: str, file_size: int):
    """Check if uploading a file would exceed storage limit"""
    current_usage = get_project_usage(project_id)
    if current_usage + file_size > STORAGE_LIMIT_PER_PROJECT:
        raise HTTPException(
            status_code=413,
            detail=f"Storage limit exceeded. Current: {current_usage/1024/1024:.2f}MB, "
            f"Limit: {STORAGE_LIMIT_PER_PROJECT/1024/1024}MB",
        )


def get_files(project_id: str):
    prefix = f"projects/{project_id}/"

    response = s3_client.list_objects_v2(Bucket=B2_BUCKET, Prefix=prefix)

    PUBLIC_BASE_URL = f"https://f005.backblazeb2.com/file/{B2_BUCKET}/"

    files = []
    if "Contents" in response:
        for obj in response["Contents"]:
            key = obj["Key"]
            filename = key.replace(prefix, "")
            if not filename:  # skip empty "directory" placeholders
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
