"""
Cloudflare R2 storage utility for Podcastfy audio files.

This module provides functions to upload, download, and manage audio files
in Cloudflare R2 storage using the S3-compatible API.
"""

import os
import boto3
from botocore.exceptions import ClientError
from .logger import setup_logger

logger = setup_logger(__name__)


class R2Storage:
    """Cloudflare R2 storage client using S3-compatible API."""
    
    def __init__(self):
        """Initialize R2 client with credentials from environment variables."""
        self.account_id = os.getenv('CLOUDFLARE_ACCOUNT_ID')
        self.access_key_id = os.getenv('R2_ACCESS_KEY_ID') 
        self.secret_access_key = os.getenv('R2_SECRET_ACCESS_KEY')
        self.bucket_name = os.getenv('R2_BUCKET_NAME', 'podcasts')
        
        if not all([self.account_id, self.access_key_id, self.secret_access_key]):
            raise ValueError("Missing R2 credentials. Please set CLOUDFLARE_ACCOUNT_ID, R2_ACCESS_KEY_ID, and R2_SECRET_ACCESS_KEY environment variables.")
        
        # Create R2 client using S3-compatible endpoint
        self.client = boto3.client(
            's3',
            endpoint_url=f'https://{self.account_id}.r2.cloudflarestorage.com',
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
            region_name='auto'  # R2 uses 'auto' region
        )
        
        logger.info(f"Initialized R2 storage client for bucket: {self.bucket_name}")
    
    def upload_audio_file(self, local_file_path: str, object_key: str) -> str:
        """
        Upload audio file to R2 storage.
        
        Args:
            local_file_path: Path to the local audio file
            object_key: Key/filename in R2 bucket (e.g., 'podcast_123.mp3')
            
        Returns:
            str: Public URL of the uploaded file
            
        Raises:
            Exception: If upload fails
        """
        try:
            # Verify local file exists
            if not os.path.exists(local_file_path):
                raise FileNotFoundError(f"Local file not found: {local_file_path}")
            
            file_size = os.path.getsize(local_file_path)
            logger.info(f"Uploading {local_file_path} to R2 as {object_key} ({file_size} bytes)")
            
            # Upload file with public-read ACL and correct content type
            self.client.upload_file(
                local_file_path,
                self.bucket_name,
                object_key,
                ExtraArgs={
                    'ContentType': 'audio/mpeg',
                    'ACL': 'public-read'
                }
            )
            
            # Generate public URL using the actual R2 dev subdomain
            public_url = f"https://pub-3b8faeb66ae44311ae8a5f29a3215bd1.r2.dev/{object_key}"
            logger.info(f"Successfully uploaded to R2: {public_url}")
            
            return public_url
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"R2 upload failed ({error_code}): {error_message}")
            raise Exception(f"R2 upload failed: {error_message}")
        except Exception as e:
            logger.error(f"Failed to upload to R2: {str(e)}")
            raise Exception(f"R2 upload error: {str(e)}")
    
    def file_exists(self, object_key: str) -> bool:
        """
        Check if a file exists in R2 storage.
        
        Args:
            object_key: Key/filename in R2 bucket
            
        Returns:
            bool: True if file exists, False otherwise
        """
        try:
            self.client.head_object(Bucket=self.bucket_name, Key=object_key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            raise
    
    def get_file_url(self, object_key: str) -> str:
        """
        Get public URL for an R2 object.
        
        Args:
            object_key: Key/filename in R2 bucket
            
        Returns:
            str: Public URL of the file
        """
        return f"https://pub-3b8faeb66ae44311ae8a5f29a3215bd1.r2.dev/{object_key}"
    
    def delete_file(self, object_key: str) -> bool:
        """
        Delete a file from R2 storage.
        
        Args:
            object_key: Key/filename in R2 bucket
            
        Returns:
            bool: True if deleted successfully
        """
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=object_key)
            logger.info(f"Deleted file from R2: {object_key}")
            return True
        except ClientError as e:
            logger.error(f"Failed to delete from R2: {str(e)}")
            return False


# Global instance for easy importing
r2_storage = None

def get_r2_storage() -> R2Storage:
    """Get singleton R2Storage instance."""
    global r2_storage
    if r2_storage is None:
        r2_storage = R2Storage()
    return r2_storage