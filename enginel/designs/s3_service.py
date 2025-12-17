"""
S3 Service for managing AWS S3 operations.

This module provides utilities for:
- Generating pre-signed URLs for uploads and downloads
- Managing S3 file operations
- Handling S3 storage paths and keys
"""

import os
import uuid
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

import boto3
from botocore.exceptions import ClientError, BotoCoreError
from botocore.config import Config
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)


class S3ServiceError(Exception):
    """Base exception for S3 service errors."""
    pass


class S3Service:
    """
    Service class for AWS S3 operations.
    
    Handles:
    - Pre-signed URL generation for uploads and downloads
    - S3 client configuration and management
    - File path and key management
    """
    
    def __init__(self):
        """Initialize S3 service with AWS credentials or R2 credentials."""
        if not settings.USE_S3:
            raise ImproperlyConfigured(
                "S3/R2 is not enabled. Set USE_S3=True in environment variables."
            )
        
        # Validate required settings
        required_settings = [
            'AWS_ACCESS_KEY_ID',
            'AWS_SECRET_ACCESS_KEY',
            'AWS_STORAGE_BUCKET_NAME',
        ]
        missing_settings = [
            s for s in required_settings 
            if not getattr(settings, s, None)
        ]
        if missing_settings:
            raise ImproperlyConfigured(
                f"Missing required AWS settings: {', '.join(missing_settings)}"
            )
        
        # Configure boto3 client
        self.config = Config(
            region_name=settings.AWS_S3_REGION_NAME,
            signature_version=settings.AWS_S3_SIGNATURE_VERSION,
            s3={
                'addressing_style': settings.AWS_S3_ADDRESSING_STYLE,
            }
        )
        
        self.client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            config=self.config
        )
        
        self.bucket_name = settings.AWS_STORAGE_BUCKET_NAME
        
        logger.info(f"S3Service initialized for bucket: {self.bucket_name}")
    
    def generate_upload_presigned_url(
        self,
        file_key: str,
        content_type: str = 'application/octet-stream',
        expiration: Optional[int] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Generate a pre-signed URL for uploading a file to S3.
        
        Args:
            file_key: S3 key (path) for the file
            content_type: MIME type of the file
            expiration: URL expiration time in seconds (default: from settings)
            metadata: Optional metadata to attach to the file
        
        Returns:
            Dictionary containing:
                - url: Pre-signed upload URL
                - fields: Form fields for POST upload (if using POST)
                - key: S3 key used
                - expires_in: Expiration time in seconds
        
        Raises:
            S3ServiceError: If URL generation fails
        """
        if expiration is None:
            expiration = settings.AWS_UPLOAD_PRESIGNED_URL_EXPIRY
        
        try:
            # Prepare parameters
            params = {
                'Bucket': self.bucket_name,
                'Key': file_key,
                'ContentType': content_type,
            }
            
            # Add metadata if provided
            if metadata:
                params['Metadata'] = metadata
            
            # Generate pre-signed URL for PUT operation
            presigned_url = self.client.generate_presigned_url(
                'put_object',
                Params=params,
                ExpiresIn=expiration,
                HttpMethod='PUT'
            )
            
            logger.info(f"Generated upload pre-signed URL for key: {file_key}")
            
            return {
                'url': presigned_url,
                'key': file_key,
                'content_type': content_type,
                'expires_in': expiration,
                'method': 'PUT',
            }
            
        except (ClientError, BotoCoreError) as e:
            logger.error(f"Failed to generate upload pre-signed URL: {str(e)}")
            raise S3ServiceError(f"Failed to generate upload URL: {str(e)}")
    
    def generate_upload_presigned_post(
        self,
        file_key: str,
        content_type: str = 'application/octet-stream',
        expiration: Optional[int] = None,
        max_file_size: int = 500 * 1024 * 1024,  # 500MB
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Generate a pre-signed POST policy for uploading a file to S3.
        
        This method is preferred for browser-based uploads as it's more secure
        and allows setting additional constraints.
        
        Args:
            file_key: S3 key (path) for the file
            content_type: MIME type of the file
            expiration: URL expiration time in seconds (default: from settings)
            max_file_size: Maximum file size in bytes (default: 500MB)
            metadata: Optional metadata to attach to the file
        
        Returns:
            Dictionary containing:
                - url: S3 endpoint URL for POST
                - fields: Form fields to include in POST request
                - key: S3 key used
                - expires_in: Expiration time in seconds
        
        Raises:
            S3ServiceError: If POST policy generation fails
        """
        if expiration is None:
            expiration = settings.AWS_UPLOAD_PRESIGNED_URL_EXPIRY
        
        try:
            # Prepare conditions
            conditions = [
                {'bucket': self.bucket_name},
                {'key': file_key},
                {'Content-Type': content_type},
                ['content-length-range', 0, max_file_size],
            ]
            
            # Add metadata conditions if provided
            fields = {'Content-Type': content_type}
            if metadata:
                for key, value in metadata.items():
                    meta_key = f'x-amz-meta-{key}'
                    fields[meta_key] = value
                    conditions.append({meta_key: value})
            
            # Generate pre-signed POST
            presigned_post = self.client.generate_presigned_post(
                Bucket=self.bucket_name,
                Key=file_key,
                Fields=fields,
                Conditions=conditions,
                ExpiresIn=expiration
            )
            
            logger.info(f"Generated upload pre-signed POST for key: {file_key}")
            
            return {
                'url': presigned_post['url'],
                'fields': presigned_post['fields'],
                'key': file_key,
                'expires_in': expiration,
                'method': 'POST',
            }
            
        except (ClientError, BotoCoreError) as e:
            logger.error(f"Failed to generate upload pre-signed POST: {str(e)}")
            raise S3ServiceError(f"Failed to generate upload POST: {str(e)}")
    
    def generate_download_presigned_url(
        self,
        file_key: str,
        expiration: Optional[int] = None,
        response_headers: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Generate a pre-signed URL for downloading a file from S3.
        
        Args:
            file_key: S3 key (path) for the file
            expiration: URL expiration time in seconds (default: from settings)
            response_headers: Optional headers to set in response (e.g., Content-Disposition)
        
        Returns:
            Pre-signed download URL
        
        Raises:
            S3ServiceError: If URL generation fails
        """
        if expiration is None:
            expiration = settings.AWS_DOWNLOAD_PRESIGNED_URL_EXPIRY
        
        try:
            # Prepare parameters
            params = {
                'Bucket': self.bucket_name,
                'Key': file_key,
            }
            
            # Add response headers if provided
            if response_headers:
                params.update(response_headers)
            
            # Generate pre-signed URL for GET operation
            presigned_url = self.client.generate_presigned_url(
                'get_object',
                Params=params,
                ExpiresIn=expiration
            )
            
            logger.info(f"Generated download pre-signed URL for key: {file_key}")
            
            return presigned_url
            
        except (ClientError, BotoCoreError) as e:
            logger.error(f"Failed to generate download pre-signed URL: {str(e)}")
            raise S3ServiceError(f"Failed to generate download URL: {str(e)}")
    
    def check_file_exists(self, file_key: str) -> bool:
        """
        Check if a file exists in S3.
        
        Args:
            file_key: S3 key (path) for the file
        
        Returns:
            True if file exists, False otherwise
        """
        try:
            self.client.head_object(Bucket=self.bucket_name, Key=file_key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            logger.error(f"Error checking file existence: {str(e)}")
            raise S3ServiceError(f"Failed to check file existence: {str(e)}")
    
    def get_file_metadata(self, file_key: str) -> Dict[str, Any]:
        """
        Get metadata for a file in S3.
        
        Args:
            file_key: S3 key (path) for the file
        
        Returns:
            Dictionary containing file metadata
        
        Raises:
            S3ServiceError: If metadata retrieval fails
        """
        try:
            response = self.client.head_object(
                Bucket=self.bucket_name,
                Key=file_key
            )
            
            return {
                'size': response.get('ContentLength'),
                'content_type': response.get('ContentType'),
                'last_modified': response.get('LastModified'),
                'etag': response.get('ETag', '').strip('"'),
                'metadata': response.get('Metadata', {}),
            }
            
        except ClientError as e:
            logger.error(f"Failed to get file metadata: {str(e)}")
            raise S3ServiceError(f"Failed to get file metadata: {str(e)}")
    
    def delete_file(self, file_key: str) -> bool:
        """
        Delete a file from S3.
        
        Args:
            file_key: S3 key (path) for the file
        
        Returns:
            True if deletion successful
        
        Raises:
            S3ServiceError: If deletion fails
        """
        try:
            self.client.delete_object(
                Bucket=self.bucket_name,
                Key=file_key
            )
            logger.info(f"Deleted file from S3: {file_key}")
            return True
            
        except (ClientError, BotoCoreError) as e:
            logger.error(f"Failed to delete file: {str(e)}")
            raise S3ServiceError(f"Failed to delete file: {str(e)}")
    
    @staticmethod
    def generate_file_key(
        organization_id: int,
        design_asset_id: int,
        filename: str,
        prefix: str = 'designs'
    ) -> str:
        """
        Generate a standardized S3 key for a file.
        
        Args:
            organization_id: Organization ID
            design_asset_id: Design asset ID
            filename: Original filename
            prefix: S3 key prefix (default: 'designs')
        
        Returns:
            S3 key in format: prefix/org_id/asset_id/unique_filename
        """
        # Add unique suffix to prevent overwrites
        name, ext = os.path.splitext(filename)
        unique_suffix = uuid.uuid4().hex[:8]
        unique_filename = f"{name}_{unique_suffix}{ext}"
        
        return f"{prefix}/{organization_id}/{design_asset_id}/{unique_filename}"
    
    @staticmethod
    def parse_file_key(file_key: str) -> Dict[str, str]:
        """
        Parse an S3 file key to extract components.
        
        Args:
            file_key: S3 key to parse
        
        Returns:
            Dictionary with parsed components (prefix, org_id, asset_id, filename)
        """
        parts = file_key.split('/')
        
        if len(parts) < 4:
            return {
                'prefix': parts[0] if len(parts) > 0 else '',
                'org_id': None,
                'asset_id': None,
                'filename': parts[-1] if len(parts) > 0 else '',
            }
        
        return {
            'prefix': parts[0],
            'org_id': parts[1],
            'asset_id': parts[2],
            'filename': '/'.join(parts[3:]),
        }


# Singleton instance
_s3_service_instance = None


def get_s3_service() -> S3Service:
    """
    Get or create the S3Service singleton instance.
    
    Returns:
        S3Service instance
    
    Raises:
        ImproperlyConfigured: If S3 is not enabled or misconfigured
    """
    global _s3_service_instance
    
    if _s3_service_instance is None:
        _s3_service_instance = S3Service()
    
    return _s3_service_instance
