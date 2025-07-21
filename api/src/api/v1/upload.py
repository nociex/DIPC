"""File upload and pre-signed URL endpoints."""

import os
import time
from datetime import datetime, timedelta
from uuid import uuid4
from pathlib import Path

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse

from ..models import PresignedUrlRequest, PresignedUrlResponse
from ...config import settings

router = APIRouter()


def get_s3_client():
    """Create and return S3 client."""
    try:
        return boto3.client(
            's3',
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key_id,
            aws_secret_access_key=settings.s3_secret_access_key,
            region_name='us-east-1'  # Default region for MinIO compatibility
        )
    except NoCredentialsError:
        raise HTTPException(
            status_code=500,
            detail="S3 credentials not configured properly"
        )


def validate_file_security(request: PresignedUrlRequest) -> None:
    """Validate file upload request for security."""
    
    # Check file size limits
    max_file_size = 100 * 1024 * 1024  # 100MB
    if request.file_size > max_file_size:
        raise HTTPException(
            status_code=413,
            detail=f"File size ({request.file_size} bytes) exceeds maximum allowed size ({max_file_size} bytes)"
        )
    
    # Check filename for security issues
    dangerous_patterns = ['..', '/', '\\', '<', '>', ':', '"', '|', '?', '*']
    for pattern in dangerous_patterns:
        if pattern in request.filename:
            raise HTTPException(
                status_code=400,
                detail=f"Filename contains dangerous pattern: {pattern}"
            )
    
    # Check for executable file extensions
    dangerous_extensions = ['.exe', '.bat', '.cmd', '.com', '.pif', '.scr', '.vbs', '.js']
    filename_lower = request.filename.lower()
    for ext in dangerous_extensions:
        if filename_lower.endswith(ext):
            raise HTTPException(
                status_code=400,
                detail=f"File type not allowed: {ext}"
            )
    
    # Validate content type matches filename extension
    content_type_mapping = {
        '.pdf': 'application/pdf',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.webp': 'image/webp',
        '.txt': 'text/plain',
        '.doc': 'application/msword',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.zip': 'application/zip'
    }
    
    # Find matching extension
    file_extension = None
    for ext in content_type_mapping:
        if filename_lower.endswith(ext):
            file_extension = ext
            break
    
    if file_extension and content_type_mapping[file_extension] != request.content_type:
        raise HTTPException(
            status_code=400,
            detail=f"Content type {request.content_type} does not match file extension {file_extension}"
        )


@router.post("/presigned-url", response_model=PresignedUrlResponse, status_code=201)
async def generate_presigned_url(request: PresignedUrlRequest):
    """Generate a pre-signed URL for file upload."""
    try:
        # Validate the request for security
        validate_file_security(request)
        
        # Generate unique file ID and key
        file_id = str(uuid4())
        file_extension = ""
        
        # Extract file extension
        if '.' in request.filename:
            file_extension = '.' + request.filename.split('.')[-1].lower()
        
        # Create object key with timestamp and unique ID
        timestamp = int(time.time())
        object_key = f"uploads/{timestamp}/{file_id}{file_extension}"
        
        # Set expiration time (1 hour from now)
        expiration_time = datetime.utcnow() + timedelta(hours=1)
        
        if settings.storage_type == "local":
            # For local storage, we'll use a direct upload endpoint
            # The upload_url will point to our local upload endpoint
            # Use the API base URL for the upload endpoint
            storage_base_url = settings.storage_base_url or "http://localhost:8000/storage"
            api_base_url = storage_base_url.replace("/storage", "")
            upload_url = f"{api_base_url}/v1/upload/upload/{file_id}"
            file_url = f"{storage_base_url}/{object_key}"
            
            # Create the upload directory if it doesn't exist
            upload_dir = Path(settings.local_storage_path) / "uploads" / str(timestamp)
            upload_dir.mkdir(parents=True, exist_ok=True)
            
            # Store the metadata for validation when the file is uploaded
            # In a production system, you'd store this in a database or cache
            # For now, we'll create a metadata file
            metadata = {
                "file_id": file_id,
                "filename": request.filename,
                "content_type": request.content_type,
                "file_size": request.file_size,
                "object_key": object_key,
                "expires_at": expiration_time.isoformat()
            }
            
            # Save metadata for validation during upload
            metadata_path = upload_dir / f"{file_id}.metadata"
            import json
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f)
            
        else:
            # S3 storage
            s3_client = get_s3_client()
            
            # Generate pre-signed URL for PUT operation
            try:
                presigned_url = s3_client.generate_presigned_url(
                    'put_object',
                    Params={
                        'Bucket': settings.s3_bucket_name,
                        'Key': object_key,
                        'ContentType': request.content_type,
                        'ContentLength': request.file_size
                    },
                    ExpiresIn=3600  # 1 hour
                )
                upload_url = presigned_url
            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code == 'NoSuchBucket':
                    raise HTTPException(
                        status_code=500,
                        detail=f"S3 bucket '{settings.s3_bucket_name}' does not exist"
                    )
                else:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to generate pre-signed URL: {str(e)}"
                    )
            
            # Construct the file URL for accessing the uploaded file
            file_url = f"{settings.s3_endpoint_url}/{settings.s3_bucket_name}/{object_key}"
        
        return PresignedUrlResponse(
            upload_url=upload_url,
            file_id=file_id,
            file_url=file_url,
            expires_at=expiration_time,
            max_file_size=request.file_size
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error generating pre-signed URL: {str(e)}"
        )


@router.post("/upload/{file_id}")
async def upload_file(file_id: str, file: UploadFile = File(...)):
    """Handle direct file upload for local storage."""
    if settings.storage_type != "local":
        raise HTTPException(
            status_code=400,
            detail="Direct upload is only available for local storage"
        )
    
    try:
        # Find metadata file
        import json
        metadata_found = False
        for timestamp_dir in Path(settings.local_storage_path).glob("uploads/*"):
            metadata_path = timestamp_dir / f"{file_id}.metadata"
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                metadata_found = True
                break
        
        if not metadata_found:
            raise HTTPException(
                status_code=404,
                detail="Upload session not found or expired"
            )
        
        # Validate file size
        file_size = 0
        temp_file = Path(settings.local_storage_path) / "temp" / f"{file_id}.tmp"
        temp_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Save uploaded file
        with open(temp_file, 'wb') as f:
            while chunk := await file.read(8192):  # Read in 8KB chunks
                file_size += len(chunk)
                if file_size > metadata['file_size']:
                    os.remove(temp_file)
                    raise HTTPException(
                        status_code=413,
                        detail=f"File size exceeds declared size of {metadata['file_size']} bytes"
                    )
                f.write(chunk)
        
        # Move file to final location
        final_path = Path(settings.local_storage_path) / metadata['object_key']
        final_path.parent.mkdir(parents=True, exist_ok=True)
        os.rename(temp_file, final_path)
        
        # Clean up metadata file
        os.remove(metadata_path)
        
        return {
            "file_id": file_id,
            "file_url": f"{settings.storage_base_url}/{metadata['object_key']}",
            "message": "File uploaded successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload file: {str(e)}"
        )


@router.get("/storage/{path:path}")
async def serve_file(path: str):
    """Serve files from local storage."""
    if settings.storage_type != "local":
        raise HTTPException(
            status_code=400,
            detail="File serving is only available for local storage"
        )
    
    file_path = Path(settings.local_storage_path) / path
    
    # Security check - ensure the path doesn't escape the storage directory
    try:
        file_path = file_path.resolve()
        Path(settings.local_storage_path).resolve()
        if not str(file_path).startswith(str(Path(settings.local_storage_path).resolve())):
            raise HTTPException(status_code=403, detail="Access denied")
    except Exception:
        raise HTTPException(status_code=403, detail="Invalid path")
    
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(file_path)


@router.get("/health")
async def upload_service_health():
    """Check upload service health including storage connectivity."""
    health_status = {
        "service": "upload",
        "status": "healthy",
        "timestamp": time.time(),
        "storage_type": settings.storage_type
    }
    
    if settings.storage_type == "local":
        # Check local storage
        health_status["local_storage"] = {
            "path": settings.local_storage_path,
            "accessible": False,
            "writable": False
        }
        
        try:
            storage_path = Path(settings.local_storage_path)
            
            # Check if storage path exists and is accessible
            if storage_path.exists():
                health_status["local_storage"]["accessible"] = True
                
                # Check if we can write to the storage path
                test_file = storage_path / ".health_check"
                try:
                    test_file.touch()
                    test_file.unlink()
                    health_status["local_storage"]["writable"] = True
                except Exception as e:
                    health_status["status"] = "degraded"
                    health_status["message"] = f"Storage path not writable: {str(e)}"
            else:
                # Try to create the storage directory
                try:
                    storage_path.mkdir(parents=True, exist_ok=True)
                    health_status["local_storage"]["accessible"] = True
                    health_status["local_storage"]["writable"] = True
                except Exception as e:
                    health_status["status"] = "unhealthy"
                    health_status["message"] = f"Cannot create storage directory: {str(e)}"
                    
        except Exception as e:
            health_status["status"] = "unhealthy"
            health_status["message"] = f"Local storage check failed: {str(e)}"
    
    else:
        # S3 storage health check
        health_status["s3_connection"] = "unknown"
        health_status["bucket_accessible"] = False
        
        try:
            # Test S3 connection
            s3_client = get_s3_client()
            
            # Test bucket access
            try:
                s3_client.head_bucket(Bucket=settings.s3_bucket_name)
                health_status["s3_connection"] = "connected"
                health_status["bucket_accessible"] = True
            except ClientError as e:
                error_code = e.response['Error']['Code']
                health_status["s3_connection"] = "connected"
                health_status["bucket_accessible"] = False
                health_status["bucket_error"] = error_code
                
                if error_code in ['NoSuchBucket', '404']:
                    health_status["status"] = "degraded"
                    health_status["message"] = f"Bucket '{settings.s3_bucket_name}' not found"
                elif error_code in ['Forbidden', '403']:
                    health_status["status"] = "degraded"
                    health_status["message"] = "Access denied to S3 bucket"
                else:
                    health_status["status"] = "unhealthy"
                    health_status["message"] = f"S3 bucket check failed: {error_code}"
            
        except NoCredentialsError:
            health_status["status"] = "unhealthy"
            health_status["s3_connection"] = "no_credentials"
            health_status["message"] = "S3 credentials not configured"
        except Exception as e:
            health_status["status"] = "unhealthy"
            health_status["s3_connection"] = "error"
            health_status["message"] = f"S3 connection failed: {str(e)}"
    
    return health_status