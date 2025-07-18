"""File upload and pre-signed URL endpoints."""

import time
from datetime import datetime, timedelta
from uuid import uuid4

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from fastapi import APIRouter, HTTPException

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
        
        # Create S3 client
        s3_client = get_s3_client()
        
        # Generate unique file ID and key
        file_id = str(uuid4())
        file_extension = ""
        
        # Extract file extension
        if '.' in request.filename:
            file_extension = '.' + request.filename.split('.')[-1].lower()
        
        # Create S3 object key with timestamp and unique ID
        timestamp = int(time.time())
        object_key = f"uploads/{timestamp}/{file_id}{file_extension}"
        
        # Set expiration time (1 hour from now)
        expiration_time = datetime.utcnow() + timedelta(hours=1)
        expiration_seconds = 3600  # 1 hour
        
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
                ExpiresIn=expiration_seconds
            )
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
        
        return PresignedUrlResponse(
            upload_url=presigned_url,
            file_id=file_id,
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


@router.get("/health")
async def upload_service_health():
    """Check upload service health including S3 connectivity."""
    health_status = {
        "service": "upload",
        "status": "healthy",
        "timestamp": time.time(),
        "s3_connection": "unknown",
        "bucket_accessible": False
    }
    
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