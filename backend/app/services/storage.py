"""
Storage service for uploading files to Cloudflare R2 (S3-compatible).
"""
import asyncio
import logging
import uuid
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Optional

import boto3
from botocore.exceptions import ClientError
from fastapi import UploadFile, HTTPException

from app.core.config import get_settings

# Thread pool for running synchronous boto3 operations
_executor = ThreadPoolExecutor(max_workers=4)

logger = logging.getLogger(__name__)

# Allowed image MIME types
ALLOWED_MIME_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}

# Magic bytes (file signatures) for validation
# These are checked against the actual file content, not the Content-Type header
MAGIC_BYTES = {
    "image/jpeg": [b"\xff\xd8\xff"],  # JPEG
    "image/png": [b"\x89PNG\r\n\x1a\n"],  # PNG
    "image/webp": [b"RIFF"],  # WebP (also check for WEBP later in file)
}

# Max file size: 5MB
MAX_FILE_SIZE = 5 * 1024 * 1024


def validate_magic_bytes(content: bytes, content_type: str) -> bool:
    """Validate file content matches expected magic bytes for the content type."""
    signatures = MAGIC_BYTES.get(content_type, [])
    for sig in signatures:
        if content.startswith(sig):
            # WebP needs additional validation for WEBP signature and chunk type
            if content_type == "image/webp":
                if len(content) < 16:
                    return False
                if content[8:12] != b"WEBP":
                    return False
                # Validate chunk type (VP8 , VP8L, VP8X are valid WebP formats)
                chunk_type = content[12:16]
                return chunk_type in (b"VP8 ", b"VP8L", b"VP8X")
            return True
    return False

# Upload type to folder mapping
UPLOAD_FOLDERS = {
    "pet-photo": "pets",
    "food-photo": "foods",
    "medicine-photo": "medicines",
    "health-event-photo": "health-events",
}


class StorageService:
    """Service for uploading and managing files in Cloudflare R2."""

    def __init__(self):
        self.settings = get_settings()
        self._client = None

    @property
    def is_configured(self) -> bool:
        """Check if S3/R2 storage is properly configured."""
        return bool(
            self.settings.s3_endpoint_url
            and self.settings.s3_access_key_id
            and self.settings.s3_secret_access_key
            and self.settings.s3_public_url
        )

    @property
    def client(self):
        """Get or create S3 client (lazy initialization)."""
        if self._client is None:
            if not self.is_configured:
                raise HTTPException(
                    status_code=503,
                    detail="Storage service not configured"
                )
            self._client = boto3.client(
                "s3",
                endpoint_url=self.settings.s3_endpoint_url,
                aws_access_key_id=self.settings.s3_access_key_id,
                aws_secret_access_key=self.settings.s3_secret_access_key,
            )
        return self._client

    async def upload_image(
        self,
        file: UploadFile,
        upload_type: str,
        family_id: str,
    ) -> str:
        """Upload an image to R2 storage.

        Args:
            file: The uploaded file
            upload_type: Type of upload (pet-photo, profile-photo, etc.)
            family_id: Family ID for folder scoping

        Returns:
            Public URL of the uploaded image

        Raises:
            HTTPException: If validation fails or upload fails
        """
        # Validate upload type
        folder = UPLOAD_FOLDERS.get(upload_type)
        if not folder:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid upload type: {upload_type}. Valid types: {list(UPLOAD_FOLDERS.keys())}"
            )

        # Validate content type
        content_type = file.content_type
        if content_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type: {content_type}. Allowed types: JPEG, PNG, WebP"
            )

        # Read file content
        content = await file.read()

        # Validate file size
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024 * 1024)}MB"
            )

        # Validate magic bytes (file signature) to prevent spoofed content types
        if not validate_magic_bytes(content, content_type):
            raise HTTPException(
                status_code=400,
                detail=f"File content does not match declared type: {content_type}"
            )

        # Generate unique key
        extension = ALLOWED_MIME_TYPES[content_type]
        file_id = str(uuid.uuid4())
        key = f"{folder}/{family_id}/{file_id}.{extension}"

        # Upload to R2 (run in thread pool to avoid blocking async event loop)
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                _executor,
                partial(
                    self.client.put_object,
                    Bucket=self.settings.s3_bucket_name,
                    Key=key,
                    Body=content,
                    ContentType=content_type,
                )
            )
            logger.info(f"Uploaded image to {key}")
        except ClientError as e:
            logger.error(f"Failed to upload to R2: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to upload image"
            )

        # Return public URL
        public_url = f"{self.settings.s3_public_url}/{key}"
        return public_url

    async def delete_image(self, url: str) -> bool:
        """Delete an image from R2 storage.

        Args:
            url: The public URL of the image to delete

        Returns:
            True if deletion was successful, False otherwise
        """
        if not self.is_configured:
            logger.warning("Storage not configured, cannot delete image")
            return False

        # Extract key from URL
        public_url_base = self.settings.s3_public_url
        if not url.startswith(public_url_base):
            logger.warning(f"URL doesn't match our storage: {url}")
            return False

        key = url.replace(f"{public_url_base}/", "")

        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                _executor,
                partial(
                    self.client.delete_object,
                    Bucket=self.settings.s3_bucket_name,
                    Key=key,
                )
            )
            logger.info(f"Deleted image: {key}")
            return True
        except ClientError as e:
            logger.error(f"Failed to delete from R2: {e}")
            return False


# Singleton instance
storage_service = StorageService()
