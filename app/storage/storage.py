from fastapi import HTTPException
from fastapi.responses import StreamingResponse
import boto3
from botocore.exceptions import ClientError
import os
from typing import Dict
import io


# B2 Configuration
B2_KEY_ID = os.getenv("B2_KEY_ID")
B2_APPLICATION_KEY = os.getenv("B2_APPLICATION_KEY")
B2_ENDPOINT = "https://s3.us-west-004.backblazeb2.com"  # Replace with your region
B2_BUCKET = os.getenv("B2_BUCKET_NAME")

# Storage limit per project (50MB in bytes)
STORAGE_LIMIT_PER_PROJECT = 50 * 1024 * 1024  # 50MB

# Initialize B2 client
s3_client = boto3.client(
    's3',
    endpoint_url=B2_ENDPOINT,
    aws_access_key_id=B2_KEY_ID,
    aws_secret_access_key=B2_APPLICATION_KEY,
)

def get_project_usage(project_id: str) -> int:
    """Get current storage usage for a project in bytes"""
    try:
        response = s3_client.list_objects_v2(
            Bucket=B2_BUCKET,
            Prefix=f"projects/{project_id}/"
        )
        
        total_size = 0
        if 'Contents' in response:
            for obj in response['Contents']:
                total_size += obj['Size']
        
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
                   f"Limit: {STORAGE_LIMIT_PER_PROJECT/1024/1024}MB"
        )

# @app.post("/projects/{project_id}/upload")
# async def upload_file(
#     project_id: str,
#     file: UploadFile = File(...)
# ):
#     """Upload a file to a project with storage limit check"""
#     try:
#         # Read file content
#         file_content = await file.read()
#         file_size = len(file_content)
        
#         # Check storage limit
#         check_storage_limit(project_id, file_size)
        
#         # Generate object key
#         object_key = f"projects/{project_id}/{file.filename}"
        
#         # Upload to B2
#         s3_client.put_object(
#             Bucket=B2_BUCKET,
#             Key=object_key,
#             Body=file_content,
#             ContentType=file.content_type or 'application/octet-stream'
#         )
        
#         return {
#             "message": "File uploaded successfully",
#             "project_id": project_id,
#             "filename": file.filename,
#             "size": file_size,
#             "storage_used": get_project_usage(project_id)
#         }
        
#     except ClientError as e:
#         raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

# @app.get("/projects/{project_id}/files/{filename}")
# async def download_file(project_id: str, filename: str):
#     """Download a file from a project"""
#     try:
#         object_key = f"projects/{project_id}/{filename}"
        
#         # Get object from B2
#         response = s3_client.get_object(Bucket=B2_BUCKET, Key=object_key)
        
#         # Stream the file content
#         def iter_content():
#             for chunk in response['Body'].iter_chunks(chunk_size=8192):
#                 yield chunk
        
#         return StreamingResponse(
#             iter_content(),
#             media_type=response.get('ContentType', 'application/octet-stream'),
#             headers={"Content-Disposition": f"attachment; filename={filename}"}
#         )
        
#     except ClientError as e:
#         if e.response['Error']['Code'] == 'NoSuchKey':
#             raise HTTPException(status_code=404, detail="File not found")
#         raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")

# @app.get("/projects/{project_id}/files")
# async def list_files(project_id: str):
#     """List all files in a project"""
#     try:
#         response = s3_client.list_objects_v2(
#             Bucket=B2_BUCKET,
#             Prefix=f"projects/{project_id}/"
#         )
        
#         files = []
#         total_size = 0
        
#         if 'Contents' in response:
#             for obj in response['Contents']:
#                 filename = obj['Key'].replace(f"projects/{project_id}/", "")
#                 if filename:  # Skip directory entries
#                     files.append({
#                         "filename": filename,
#                         "size": obj['Size'],
#                         "last_modified": obj['LastModified'].isoformat()
#                     })
#                     total_size += obj['Size']
        
#         return {
#             "project_id": project_id,
#             "files": files,
#             "total_files": len(files),
#             "storage_used": total_size,
#             "storage_limit": STORAGE_LIMIT_PER_PROJECT,
#             "storage_remaining": STORAGE_LIMIT_PER_PROJECT - total_size
#         }
        
#     except ClientError as e:
#         raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")

# @app.delete("/projects/{project_id}/files/{filename}")
# async def delete_file(project_id: str, filename: str):
#     """Delete a file from a project"""
#     try:
#         object_key = f"projects/{project_id}/{filename}"
        
#         s3_client.delete_object(Bucket=B2_BUCKET, Key=object_key)
        
#         return {
#             "message": "File deleted successfully",
#             "project_id": project_id,
#             "filename": filename,
#             "storage_used": get_project_usage(project_id)
#         }
        
#     except ClientError as e:
#         raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")

# @app.get("/projects/{project_id}/storage")
# async def get_storage_info(project_id: str):
#     """Get storage information for a project"""
#     usage = get_project_usage(project_id)
    
#     return {
#         "project_id": project_id,
#         "storage_used": usage,
#         "storage_used_mb": round(usage / 1024 / 1024, 2),
#         "storage_limit": STORAGE_LIMIT_PER_PROJECT,
#         "storage_limit_mb": STORAGE_LIMIT_PER_PROJECT / 1024 / 1024,
#         "storage_remaining": STORAGE_LIMIT_PER_PROJECT - usage,
#         "storage_remaining_mb": round((STORAGE_LIMIT_PER_PROJECT - usage) / 1024 / 1024, 2),
#         "usage_percentage": round((usage / STORAGE_LIMIT_PER_PROJECT) * 100, 2)
#     }
