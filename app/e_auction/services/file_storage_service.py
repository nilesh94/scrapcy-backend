"""
File Storage Service
Abstract storage layer - supports multiple providers
Configured via ENV: STORAGE_PROVIDER
"""
import os
import shutil
from typing import Optional
from datetime import datetime, timezone
from pathlib import Path
import mimetypes

from app.e_auction.config import settings
from app.e_auction.utils.exceptions import FileUploadFailedException, InvalidFileTypeException


class FileStorageService:
    """
    File storage abstraction layer
    Supports: local, google_sheets (future), s3 (future), oci (future)
    """
    
    def __init__(self):
        self.provider = settings.STORAGE_PROVIDER
        self.local_dir = Path(settings.LOCAL_UPLOAD_DIR)
        
        # Create local directory if using local storage
        if self.provider == "local":
            self.local_dir.mkdir(parents=True, exist_ok=True)
    
    async def upload_file(
        self,
        file_content: bytes,
        file_name: str,
        folder: str = "general",
        allowed_extensions: Optional[list] = None
    ) -> dict:
        """
        Upload file to configured storage
        
        Args:
            file_content: File bytes
            file_name: Original filename
            folder: Folder/category (e.g., 'auction_docs', 'lot_images')
            allowed_extensions: List of allowed extensions (e.g., ['.jpg', '.pdf'])
            
        Returns:
            dict with url, file_name, file_size, mime_type
        """
        # Validate file extension
        file_ext = Path(file_name).suffix.lower()
        if allowed_extensions and file_ext not in allowed_extensions:
            raise InvalidFileTypeException(allowed_extensions)
        
        # Generate unique filename
        # SaaS FIX: Use UTC for unique filename timestamp
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        unique_name = f"{timestamp}_{file_name}"
        
        # Route to appropriate storage
        if self.provider == "local":
            return await self._upload_local(file_content, unique_name, folder)
        elif self.provider == "google_sheets":
            return await self._upload_google_sheets(file_content, unique_name, folder)
        elif self.provider == "s3":
            return await self._upload_s3(file_content, unique_name, folder)
        elif self.provider == "oci":
            return await self._upload_oci(file_content, unique_name, folder)
        else:
            raise FileUploadFailedException(f"Unsupported storage provider: {self.provider}")
    
    async def _upload_local(self, file_content: bytes, file_name: str, folder: str) -> dict:
        """Upload to local filesystem"""
        try:
            # Create folder path
            folder_path = self.local_dir / folder
            folder_path.mkdir(parents=True, exist_ok=True)
            
            # Full file path
            file_path = folder_path / file_name
            
            # Write file
            with open(file_path, 'wb') as f:
                f.write(file_content)
            
            # Generate URL (relative to backend)
            file_url = f"{settings.BACKEND_URL}/uploads/{folder}/{file_name}"
            
            # Get file info
            file_size = len(file_content)
            mime_type = mimetypes.guess_type(file_name)[0] or 'application/octet-stream'
            
            return {
                'url': file_url,
                'file_name': file_name,
                'file_size': file_size,
                'mime_type': mime_type,
                'provider': 'local'
            }
        
        except Exception as e:
            raise FileUploadFailedException(f"Local upload failed: {str(e)}")
    
    async def _upload_google_sheets(self, file_content: bytes, file_name: str, folder: str) -> dict:
        """
        Upload to Google Sheets / Google Drive
        TODO: Implement when you provide credentials
        """
        # Placeholder - will implement when you provide Google Sheets API credentials
        raise FileUploadFailedException("Google Sheets storage not yet implemented. Please provide credentials.")
        
        # Future implementation:
        """
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        
        credentials = service_account.Credentials.from_service_account_file(
            settings.GOOGLE_SHEETS_CREDENTIALS_FILE
        )
        
        drive_service = build('drive', 'v3', credentials=credentials)
        
        # Upload to Google Drive
        file_metadata = {
            'name': file_name,
            'parents': [settings.GOOGLE_SHEETS_FOLDER_ID]
        }
        
        # Upload and get link
        # Return dict with url, file_name, file_size, mime_type
        """
    
    async def _upload_s3(self, file_content: bytes, file_name: str, folder: str) -> dict:
        """
        Upload to AWS S3
        Only used if STORAGE_PROVIDER=s3 in ENV
        """
        try:
            import boto3
            
            s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION
            )
            
            # Upload
            object_key = f"{folder}/{file_name}"
            s3_client.put_object(
                Bucket=settings.AWS_S3_BUCKET,
                Key=object_key,
                Body=file_content
            )
            
            # Generate URL
            file_url = f"{settings.AWS_S3_PUBLIC_URL}/{object_key}"
            
            return {
                'url': file_url,
                'file_name': file_name,
                'file_size': len(file_content),
                'mime_type': mimetypes.guess_type(file_name)[0],
                'provider': 's3'
            }
        
        except ImportError:
            raise FileUploadFailedException("boto3 not installed. Install with: pip install boto3")
        except Exception as e:
            raise FileUploadFailedException(f"S3 upload failed: {str(e)}")
    
    async def _upload_oci(self, file_content: bytes, file_name: str, folder: str) -> dict:
        """
        Upload to Oracle Cloud Infrastructure Object Storage
        Only used if STORAGE_PROVIDER=oci in ENV
        """
        try:
            import oci
            
            # OCI configuration
            config = oci.config.from_file(
                file_location=settings.OCI_CONFIG_FILE,
                profile_name=settings.OCI_CONFIG_PROFILE
            )
            
            object_storage = oci.object_storage.ObjectStorageClient(config)
            namespace = settings.OCI_NAMESPACE
            
            # Upload
            object_name = f"{folder}/{file_name}"
            object_storage.put_object(
                namespace,
                settings.OCI_BUCKET,
                object_name,
                file_content
            )
            
            # Generate URL
            file_url = f"https://objectstorage.{settings.OCI_REGION}.oraclecloud.com/n/{namespace}/b/{settings.OCI_BUCKET}/o/{object_name}"
            
            return {
                'url': file_url,
                'file_name': file_name,
                'file_size': len(file_content),
                'mime_type': mimetypes.guess_type(file_name)[0],
                'provider': 'oci'
            }
        
        except ImportError:
            raise FileUploadFailedException("oci not installed. Install with: pip install oci")
        except Exception as e:
            raise FileUploadFailedException(f"OCI upload failed: {str(e)}")
    
    async def delete_file(self, file_url: str) -> bool:
        """Delete file from storage"""
        # Implementation depends on storage provider
        # For now, return True
        return True


# Singleton instance
file_storage_service = FileStorageService()
