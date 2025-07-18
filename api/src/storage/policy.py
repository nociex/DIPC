"""Storage policy management and enforcement utilities."""

import os
import boto3
import structlog
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from sqlalchemy.orm import Session
from botocore.exceptions import ClientError

from ..database.models import FileMetadata, StoragePolicyEnum
from ..database.connection import get_db_session
from ..config import settings

logger = structlog.get_logger(__name__)


@dataclass
class StorageUsageStats:
    """Storage usage statistics."""
    total_files: int
    total_size_bytes: int
    permanent_files: int
    permanent_size_bytes: int
    temporary_files: int
    temporary_size_bytes: int
    expired_files: int
    expired_size_bytes: int


@dataclass
class StoragePolicyConfig:
    """Storage policy configuration."""
    policy: StoragePolicyEnum
    ttl_hours: Optional[int] = None
    max_file_size: Optional[int] = None
    allowed_extensions: Optional[List[str]] = None
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.policy == StoragePolicyEnum.TEMPORARY and self.ttl_hours is None:
            self.ttl_hours = settings.temp_file_ttl_hours


class StoragePolicyManager:
    """Manages storage policies and TTL enforcement."""
    
    def __init__(self, s3_client=None):
        """Initialize storage policy manager."""
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
    
    def apply_storage_policy(
        self, 
        file_metadata: FileMetadata, 
        policy_config: StoragePolicyConfig
    ) -> FileMetadata:
        """
        Apply storage policy to file metadata.
        
        Args:
            file_metadata: File metadata to update
            policy_config: Storage policy configuration
            
        Returns:
            Updated file metadata
        """
        logger.info(
            "Applying storage policy",
            file_id=str(file_metadata.id),
            policy=policy_config.policy.value,
            ttl_hours=policy_config.ttl_hours
        )
        
        # Update storage policy
        file_metadata.storage_policy = policy_config.policy
        
        # Set expiration for temporary files
        if policy_config.policy == StoragePolicyEnum.TEMPORARY and policy_config.ttl_hours:
            file_metadata.expires_at = datetime.now(timezone.utc) + timedelta(
                hours=policy_config.ttl_hours
            )
        else:
            file_metadata.expires_at = None
            
        return file_metadata
    
    def validate_file_against_policy(
        self, 
        file_size: int, 
        file_extension: str, 
        policy_config: StoragePolicyConfig
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate file against storage policy constraints.
        
        Args:
            file_size: Size of file in bytes
            file_extension: File extension
            policy_config: Storage policy configuration
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check file size limits
        if policy_config.max_file_size and file_size > policy_config.max_file_size:
            return False, f"File size ({file_size} bytes) exceeds policy limit ({policy_config.max_file_size} bytes)"
        
        # Check allowed extensions
        if policy_config.allowed_extensions:
            if file_extension.lower() not in [ext.lower() for ext in policy_config.allowed_extensions]:
                return False, f"File extension '{file_extension}' not allowed by policy"
        
        return True, None
    
    def get_default_policy_config(self, storage_policy: str = None) -> StoragePolicyConfig:
        """
        Get default storage policy configuration.
        
        Args:
            storage_policy: Override default storage policy
            
        Returns:
            Storage policy configuration
        """
        policy_str = storage_policy or settings.default_storage_policy
        policy = StoragePolicyEnum(policy_str)
        
        return StoragePolicyConfig(
            policy=policy,
            ttl_hours=settings.temp_file_ttl_hours if policy == StoragePolicyEnum.TEMPORARY else None,
            max_file_size=None,  # No default limit
            allowed_extensions=None  # Allow all extensions by default
        )
    
    def update_file_policy(
        self, 
        file_id: str, 
        new_policy: StoragePolicyEnum,
        ttl_hours: Optional[int] = None
    ) -> bool:
        """
        Update storage policy for existing file.
        
        Args:
            file_id: File metadata ID
            new_policy: New storage policy
            ttl_hours: TTL hours for temporary policy
            
        Returns:
            True if updated successfully
        """
        try:
            with get_db_session() as db:
                file_metadata = db.query(FileMetadata).filter(
                    FileMetadata.id == file_id
                ).first()
                
                if not file_metadata:
                    logger.warning("File metadata not found", file_id=file_id)
                    return False
                
                old_policy = file_metadata.storage_policy
                
                # Create policy config
                policy_config = StoragePolicyConfig(
                    policy=new_policy,
                    ttl_hours=ttl_hours or settings.temp_file_ttl_hours
                )
                
                # Apply new policy
                self.apply_storage_policy(file_metadata, policy_config)
                
                db.commit()
                
                logger.info(
                    "Updated file storage policy",
                    file_id=file_id,
                    old_policy=old_policy.value,
                    new_policy=new_policy.value,
                    expires_at=file_metadata.expires_at
                )
                
                return True
                
        except Exception as e:
            logger.error("Failed to update file policy", file_id=file_id, error=str(e))
            return False
    
    def enforce_storage_policies(self) -> Dict[str, Any]:
        """
        Enforce storage policies across all files.
        
        Returns:
            Dictionary with enforcement results
        """
        logger.info("Starting storage policy enforcement")
        
        results = {
            "files_processed": 0,
            "policies_updated": 0,
            "errors": []
        }
        
        try:
            with get_db_session() as db:
                # Get all files that need policy enforcement
                files = db.query(FileMetadata).all()
                
                for file_metadata in files:
                    results["files_processed"] += 1
                    
                    try:
                        # Check if temporary file needs expiration update
                        if (file_metadata.storage_policy == StoragePolicyEnum.TEMPORARY and 
                            file_metadata.expires_at is None):
                            
                            file_metadata.expires_at = datetime.now(timezone.utc) + timedelta(
                                hours=settings.temp_file_ttl_hours
                            )
                            results["policies_updated"] += 1
                            
                    except Exception as e:
                        error_msg = f"Failed to enforce policy for file {file_metadata.id}: {str(e)}"
                        results["errors"].append(error_msg)
                        logger.error("Policy enforcement error", file_id=str(file_metadata.id), error=str(e))
                
                db.commit()
                
        except Exception as e:
            error_msg = f"Storage policy enforcement failed: {str(e)}"
            results["errors"].append(error_msg)
            logger.error("Storage policy enforcement failed", error=str(e))
        
        logger.info("Storage policy enforcement completed", **results)
        return results


class StorageUsageTracker:
    """Tracks storage usage and provides analytics."""
    
    def __init__(self, s3_client=None):
        """Initialize storage usage tracker."""
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
    
    def get_storage_usage_stats(self) -> StorageUsageStats:
        """
        Get comprehensive storage usage statistics.
        
        Returns:
            Storage usage statistics
        """
        logger.info("Calculating storage usage statistics")
        
        try:
            with get_db_session() as db:
                files = db.query(FileMetadata).all()
                
                total_files = len(files)
                total_size = sum(f.file_size for f in files)
                
                permanent_files = [f for f in files if f.storage_policy == StoragePolicyEnum.PERMANENT]
                permanent_size = sum(f.file_size for f in permanent_files)
                
                temporary_files = [f for f in files if f.storage_policy == StoragePolicyEnum.TEMPORARY]
                temporary_size = sum(f.file_size for f in temporary_files)
                
                expired_files = [f for f in temporary_files if f.is_expired()]
                expired_size = sum(f.file_size for f in expired_files)
                
                stats = StorageUsageStats(
                    total_files=total_files,
                    total_size_bytes=total_size,
                    permanent_files=len(permanent_files),
                    permanent_size_bytes=permanent_size,
                    temporary_files=len(temporary_files),
                    temporary_size_bytes=temporary_size,
                    expired_files=len(expired_files),
                    expired_size_bytes=expired_size
                )
                
                logger.info(
                    "Storage usage calculated",
                    total_files=stats.total_files,
                    total_size_mb=round(stats.total_size_bytes / 1024 / 1024, 2),
                    expired_files=stats.expired_files,
                    expired_size_mb=round(stats.expired_size_bytes / 1024 / 1024, 2)
                )
                
                return stats
                
        except Exception as e:
            logger.error("Failed to calculate storage usage", error=str(e))
            # Return empty stats on error
            return StorageUsageStats(0, 0, 0, 0, 0, 0, 0, 0)
    
    def get_usage_by_user(self, user_id: str) -> Dict[str, Any]:
        """
        Get storage usage statistics for specific user.
        
        Args:
            user_id: User identifier
            
        Returns:
            User-specific storage statistics
        """
        try:
            with get_db_session() as db:
                # Get files for user through task relationship
                files = db.query(FileMetadata).join(
                    FileMetadata.task
                ).filter_by(user_id=user_id).all()
                
                if not files:
                    return {
                        "user_id": user_id,
                        "total_files": 0,
                        "total_size_bytes": 0,
                        "permanent_files": 0,
                        "temporary_files": 0,
                        "expired_files": 0
                    }
                
                permanent_files = [f for f in files if f.storage_policy == StoragePolicyEnum.PERMANENT]
                temporary_files = [f for f in files if f.storage_policy == StoragePolicyEnum.TEMPORARY]
                expired_files = [f for f in temporary_files if f.is_expired()]
                
                return {
                    "user_id": user_id,
                    "total_files": len(files),
                    "total_size_bytes": sum(f.file_size for f in files),
                    "permanent_files": len(permanent_files),
                    "temporary_files": len(temporary_files),
                    "expired_files": len(expired_files)
                }
                
        except Exception as e:
            logger.error("Failed to get user storage usage", user_id=user_id, error=str(e))
            return {
                "user_id": user_id,
                "error": str(e)
            }
    
    def verify_s3_storage_consistency(self) -> Dict[str, Any]:
        """
        Verify consistency between database records and S3 storage.
        
        Returns:
            Consistency check results
        """
        logger.info("Starting S3 storage consistency check")
        
        results = {
            "database_files": 0,
            "s3_objects": 0,
            "missing_in_s3": [],
            "orphaned_in_s3": [],
            "size_mismatches": []
        }
        
        try:
            # Get all files from database
            with get_db_session() as db:
                db_files = db.query(FileMetadata).all()
                results["database_files"] = len(db_files)
                
                db_paths = {f.storage_path: f for f in db_files}
            
            # List all objects in S3 bucket
            try:
                paginator = self.s3_client.get_paginator('list_objects_v2')
                s3_objects = []
                
                for page in paginator.paginate(Bucket=self.bucket_name):
                    if 'Contents' in page:
                        s3_objects.extend(page['Contents'])
                
                results["s3_objects"] = len(s3_objects)
                s3_keys = {obj['Key'] for obj in s3_objects}
                
                # Find missing files in S3
                for db_path, file_metadata in db_paths.items():
                    if db_path not in s3_keys:
                        results["missing_in_s3"].append({
                            "file_id": str(file_metadata.id),
                            "path": db_path,
                            "filename": file_metadata.original_filename
                        })
                
                # Find orphaned files in S3
                for s3_key in s3_keys:
                    if s3_key not in db_paths:
                        results["orphaned_in_s3"].append(s3_key)
                
                # Check size consistency for existing files
                for obj in s3_objects:
                    if obj['Key'] in db_paths:
                        db_file = db_paths[obj['Key']]
                        if db_file.file_size != obj['Size']:
                            results["size_mismatches"].append({
                                "file_id": str(db_file.id),
                                "path": obj['Key'],
                                "db_size": db_file.file_size,
                                "s3_size": obj['Size']
                            })
                
            except ClientError as e:
                logger.error("Failed to list S3 objects", error=str(e))
                results["s3_error"] = str(e)
                
        except Exception as e:
            logger.error("Storage consistency check failed", error=str(e))
            results["error"] = str(e)
        
        logger.info(
            "Storage consistency check completed",
            missing_in_s3=len(results["missing_in_s3"]),
            orphaned_in_s3=len(results["orphaned_in_s3"]),
            size_mismatches=len(results["size_mismatches"])
        )
        
        return results