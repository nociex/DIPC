"""Storage cleanup service for managing temporary files and TTL enforcement."""

import os
import boto3
import structlog
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from sqlalchemy.orm import Session
from sqlalchemy import and_
from botocore.exceptions import ClientError

from ..database.models import FileMetadata, StoragePolicyEnum
from ..database.connection import get_db_session
from ..config import settings

logger = structlog.get_logger(__name__)


@dataclass
class CleanupResult:
    """Result of cleanup operation."""
    files_processed: int
    files_deleted: int
    bytes_freed: int
    errors: List[str]
    duration_seconds: float


class StorageCleanupService:
    """Service for cleaning up expired temporary files."""
    
    def __init__(self, s3_client=None):
        """Initialize storage cleanup service."""
        self.s3_client = s3_client or self._create_s3_client()
        self.bucket_name = settings.s3_bucket_name
        
    def _create_s3_client(self):
        """Create S3 client with configuration."""
        return boto3.client(
            's3',
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key_id,
            aws_secret_access_key=settings.s3_secret_access_key
        )
    
    def get_expired_files(self, limit: int = 1000) -> List[FileMetadata]:
        """
        Get list of expired temporary files.
        
        Args:
            limit: Maximum number of files to return
            
        Returns:
            List of expired file metadata
        """
        try:
            with get_db_session() as db:
                now = datetime.now(timezone.utc)
                
                expired_files = db.query(FileMetadata).filter(
                    and_(
                        FileMetadata.storage_policy == StoragePolicyEnum.TEMPORARY,
                        FileMetadata.expires_at < now
                    )
                ).limit(limit).all()
                
                logger.info(
                    "Found expired files",
                    count=len(expired_files),
                    limit=limit
                )
                
                return expired_files
                
        except Exception as e:
            logger.error("Failed to get expired files", error=str(e))
            return []
    
    def delete_file_from_storage(self, storage_path: str) -> bool:
        """
        Delete file from S3 storage.
        
        Args:
            storage_path: Path to file in storage
            
        Returns:
            True if deleted successfully
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=storage_path
            )
            
            logger.debug("Deleted file from S3", path=storage_path)
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.warning("File not found in S3", path=storage_path)
                return True  # Consider missing file as successfully "deleted"
            else:
                logger.error("Failed to delete file from S3", path=storage_path, error=str(e))
                return False
                
        except Exception as e:
            logger.error("Unexpected error deleting file from S3", path=storage_path, error=str(e))
            return False
    
    def delete_file_metadata(self, file_metadata: FileMetadata) -> bool:
        """
        Delete file metadata from database.
        
        Args:
            file_metadata: File metadata to delete
            
        Returns:
            True if deleted successfully
        """
        try:
            with get_db_session() as db:
                # Re-query to ensure we have the latest version
                file_to_delete = db.query(FileMetadata).filter(
                    FileMetadata.id == file_metadata.id
                ).first()
                
                if file_to_delete:
                    db.delete(file_to_delete)
                    db.commit()
                    
                    logger.debug(
                        "Deleted file metadata",
                        file_id=str(file_metadata.id),
                        filename=file_metadata.original_filename
                    )
                    return True
                else:
                    logger.warning("File metadata not found", file_id=str(file_metadata.id))
                    return True  # Consider missing metadata as successfully "deleted"
                    
        except Exception as e:
            logger.error(
                "Failed to delete file metadata",
                file_id=str(file_metadata.id),
                error=str(e)
            )
            return False
    
    def cleanup_expired_files(self, batch_size: int = 100, dry_run: bool = False) -> CleanupResult:
        """
        Clean up expired temporary files.
        
        Args:
            batch_size: Number of files to process in each batch
            dry_run: If True, only simulate cleanup without actual deletion
            
        Returns:
            Cleanup operation results
        """
        start_time = datetime.now()
        logger.info(
            "Starting expired files cleanup",
            batch_size=batch_size,
            dry_run=dry_run
        )
        
        result = CleanupResult(
            files_processed=0,
            files_deleted=0,
            bytes_freed=0,
            errors=[],
            duration_seconds=0.0
        )
        
        try:
            expired_files = self.get_expired_files(limit=batch_size)
            result.files_processed = len(expired_files)
            
            for file_metadata in expired_files:
                try:
                    if dry_run:
                        logger.info(
                            "Would delete expired file (dry run)",
                            file_id=str(file_metadata.id),
                            filename=file_metadata.original_filename,
                            size_bytes=file_metadata.file_size,
                            expired_at=file_metadata.expires_at
                        )
                        result.files_deleted += 1
                        result.bytes_freed += file_metadata.file_size
                        continue
                    
                    # Delete from S3 storage
                    storage_deleted = self.delete_file_from_storage(file_metadata.storage_path)
                    
                    # Delete metadata from database
                    metadata_deleted = self.delete_file_metadata(file_metadata)
                    
                    if storage_deleted and metadata_deleted:
                        result.files_deleted += 1
                        result.bytes_freed += file_metadata.file_size
                        
                        logger.info(
                            "Successfully deleted expired file",
                            file_id=str(file_metadata.id),
                            filename=file_metadata.original_filename,
                            size_bytes=file_metadata.file_size
                        )
                    else:
                        error_msg = f"Partial deletion failure for file {file_metadata.id}"
                        result.errors.append(error_msg)
                        logger.error(error_msg)
                        
                except Exception as e:
                    error_msg = f"Failed to delete file {file_metadata.id}: {str(e)}"
                    result.errors.append(error_msg)
                    logger.error(
                        "File deletion failed",
                        file_id=str(file_metadata.id),
                        error=str(e)
                    )
            
        except Exception as e:
            error_msg = f"Cleanup operation failed: {str(e)}"
            result.errors.append(error_msg)
            logger.error("Cleanup operation failed", error=str(e))
        
        # Calculate duration
        end_time = datetime.now()
        result.duration_seconds = (end_time - start_time).total_seconds()
        
        logger.info(
            "Expired files cleanup completed",
            files_processed=result.files_processed,
            files_deleted=result.files_deleted,
            bytes_freed=result.bytes_freed,
            errors_count=len(result.errors),
            duration_seconds=result.duration_seconds,
            dry_run=dry_run
        )
        
        return result
    
    def cleanup_orphaned_files(self, dry_run: bool = False) -> CleanupResult:
        """
        Clean up orphaned files in S3 that have no database records.
        
        Args:
            dry_run: If True, only simulate cleanup without actual deletion
            
        Returns:
            Cleanup operation results
        """
        start_time = datetime.now()
        logger.info("Starting orphaned files cleanup", dry_run=dry_run)
        
        result = CleanupResult(
            files_processed=0,
            files_deleted=0,
            bytes_freed=0,
            errors=[],
            duration_seconds=0.0
        )
        
        try:
            # Get all storage paths from database
            with get_db_session() as db:
                db_paths = set(
                    path[0] for path in db.query(FileMetadata.storage_path).all()
                )
            
            # List all objects in S3
            paginator = self.s3_client.get_paginator('list_objects_v2')
            
            for page in paginator.paginate(Bucket=self.bucket_name):
                if 'Contents' not in page:
                    continue
                    
                for obj in page['Contents']:
                    result.files_processed += 1
                    
                    # Check if object exists in database
                    if obj['Key'] not in db_paths:
                        try:
                            if dry_run:
                                logger.info(
                                    "Would delete orphaned file (dry run)",
                                    path=obj['Key'],
                                    size_bytes=obj['Size']
                                )
                                result.files_deleted += 1
                                result.bytes_freed += obj['Size']
                                continue
                            
                            # Delete orphaned file
                            self.s3_client.delete_object(
                                Bucket=self.bucket_name,
                                Key=obj['Key']
                            )
                            
                            result.files_deleted += 1
                            result.bytes_freed += obj['Size']
                            
                            logger.info(
                                "Deleted orphaned file",
                                path=obj['Key'],
                                size_bytes=obj['Size']
                            )
                            
                        except Exception as e:
                            error_msg = f"Failed to delete orphaned file {obj['Key']}: {str(e)}"
                            result.errors.append(error_msg)
                            logger.error("Orphaned file deletion failed", path=obj['Key'], error=str(e))
            
        except Exception as e:
            error_msg = f"Orphaned files cleanup failed: {str(e)}"
            result.errors.append(error_msg)
            logger.error("Orphaned files cleanup failed", error=str(e))
        
        # Calculate duration
        end_time = datetime.now()
        result.duration_seconds = (end_time - start_time).total_seconds()
        
        logger.info(
            "Orphaned files cleanup completed",
            files_processed=result.files_processed,
            files_deleted=result.files_deleted,
            bytes_freed=result.bytes_freed,
            errors_count=len(result.errors),
            duration_seconds=result.duration_seconds,
            dry_run=dry_run
        )
        
        return result
    
    def get_cleanup_candidates(self, days_ahead: int = 1) -> List[Dict[str, Any]]:
        """
        Get files that will expire within specified days.
        
        Args:
            days_ahead: Number of days to look ahead for expiring files
            
        Returns:
            List of files that will expire soon
        """
        try:
            with get_db_session() as db:
                future_time = datetime.now(timezone.utc) + timedelta(days=days_ahead)
                
                expiring_files = db.query(FileMetadata).filter(
                    and_(
                        FileMetadata.storage_policy == StoragePolicyEnum.TEMPORARY,
                        FileMetadata.expires_at <= future_time,
                        FileMetadata.expires_at > datetime.now(timezone.utc)
                    )
                ).all()
                
                candidates = []
                for file_metadata in expiring_files:
                    candidates.append({
                        "file_id": str(file_metadata.id),
                        "filename": file_metadata.original_filename,
                        "size_bytes": file_metadata.file_size,
                        "expires_at": file_metadata.expires_at,
                        "storage_path": file_metadata.storage_path,
                        "task_id": str(file_metadata.task_id)
                    })
                
                logger.info(
                    "Found cleanup candidates",
                    count=len(candidates),
                    days_ahead=days_ahead
                )
                
                return candidates
                
        except Exception as e:
            logger.error("Failed to get cleanup candidates", error=str(e))
            return []
    
    def extend_file_ttl(self, file_id: str, additional_hours: int) -> bool:
        """
        Extend TTL for a temporary file.
        
        Args:
            file_id: File metadata ID
            additional_hours: Hours to add to current expiration
            
        Returns:
            True if extended successfully
        """
        try:
            with get_db_session() as db:
                file_metadata = db.query(FileMetadata).filter(
                    FileMetadata.id == file_id
                ).first()
                
                if not file_metadata:
                    logger.warning("File metadata not found", file_id=file_id)
                    return False
                
                if file_metadata.storage_policy != StoragePolicyEnum.TEMPORARY:
                    logger.warning("Cannot extend TTL for non-temporary file", file_id=file_id)
                    return False
                
                if file_metadata.expires_at:
                    new_expiration = file_metadata.expires_at + timedelta(hours=additional_hours)
                else:
                    new_expiration = datetime.now(timezone.utc) + timedelta(hours=additional_hours)
                
                file_metadata.expires_at = new_expiration
                db.commit()
                
                logger.info(
                    "Extended file TTL",
                    file_id=file_id,
                    additional_hours=additional_hours,
                    new_expiration=new_expiration
                )
                
                return True
                
        except Exception as e:
            logger.error("Failed to extend file TTL", file_id=file_id, error=str(e))
            return False