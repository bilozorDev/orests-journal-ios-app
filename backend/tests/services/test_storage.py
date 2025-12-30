"""
Comprehensive unit tests for storage service (Cloudflare R2/S3).

Tests cover:
- StorageService initialization and configuration validation
- upload_image: validation (type, size, magic bytes), upload success/failure
- delete_image: URL extraction, deletion success/failure
- Error handling (invalid files, S3 failures, unconfigured service)
- Edge cases (missing config, invalid URLs, boundary values)

All external dependencies (boto3 S3 client) are mocked for isolated unit testing.
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

import pytest
from botocore.exceptions import ClientError
from fastapi import HTTPException

from app.services.storage import (
    StorageService,
    storage_service,
    validate_magic_bytes,
    ALLOWED_MIME_TYPES,
    UPLOAD_FOLDERS,
    MAX_FILE_SIZE,
)


# ============== Test Data ==============

# Valid JPEG magic bytes
VALID_JPEG_BYTES = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01" + b"\x00" * 100

# Valid PNG magic bytes
VALID_PNG_BYTES = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"\x00" * 100

# Valid WebP magic bytes (RIFF + WEBP + VP8 chunk type)
VALID_WEBP_BYTES = b"RIFF" + b"\x00\x00\x00\x00" + b"WEBPVP8 " + b"\x00" * 100

# Invalid magic bytes
INVALID_JPEG_BYTES = b"\x00\x00\x00\x00" + b"\x00" * 100

# Small valid JPEG (under size limit)
SMALL_JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 1000

# Large file (over 5MB limit)
LARGE_FILE = b"\xff\xd8\xff\xe0" + b"\x00" * (6 * 1024 * 1024)

TEST_ORG_ID = str(uuid4())
TEST_BUCKET = "test-bucket"
TEST_ENDPOINT = "https://test.r2.cloudflarestorage.com"
TEST_PUBLIC_URL = "https://cdn.example.com"
TEST_ACCESS_KEY = "test-access-key"
TEST_SECRET_KEY = "test-secret-key"


# ============== Mock Helpers ==============

def create_mock_upload_file(
    filename: str = "test.jpg",
    content_type: str = "image/jpeg",
    content: bytes = VALID_JPEG_BYTES,
) -> MagicMock:
    """Create a mock UploadFile object."""
    upload_file = MagicMock()
    upload_file.filename = filename
    upload_file.content_type = content_type
    upload_file.read = AsyncMock(return_value=content)
    return upload_file


def create_mock_settings(
    s3_endpoint_url: str = TEST_ENDPOINT,
    s3_access_key_id: str = TEST_ACCESS_KEY,
    s3_secret_access_key: str = TEST_SECRET_KEY,
    s3_bucket_name: str = TEST_BUCKET,
    s3_public_url: str = TEST_PUBLIC_URL,
) -> Mock:
    """Create mock settings object."""
    settings = Mock()
    settings.s3_endpoint_url = s3_endpoint_url
    settings.s3_access_key_id = s3_access_key_id
    settings.s3_secret_access_key = s3_secret_access_key
    settings.s3_bucket_name = s3_bucket_name
    settings.s3_public_url = s3_public_url
    return settings


# ============== validate_magic_bytes Tests ==============

class TestValidateMagicBytes:
    """Test validate_magic_bytes function."""

    def test_valid_jpeg_bytes(self):
        """Should return True for valid JPEG magic bytes."""
        assert validate_magic_bytes(VALID_JPEG_BYTES, "image/jpeg") is True

    def test_valid_png_bytes(self):
        """Should return True for valid PNG magic bytes."""
        assert validate_magic_bytes(VALID_PNG_BYTES, "image/png") is True

    def test_valid_webp_bytes(self):
        """Should return True for valid WebP magic bytes with proper chunk type."""
        assert validate_magic_bytes(VALID_WEBP_BYTES, "image/webp") is True

    def test_valid_webp_vp8l_chunk(self):
        """Should return True for WebP with VP8L chunk type."""
        webp_vp8l = b"RIFF" + b"\x00\x00\x00\x00" + b"WEBPVP8L" + b"\x00" * 100
        assert validate_magic_bytes(webp_vp8l, "image/webp") is True

    def test_valid_webp_vp8x_chunk(self):
        """Should return True for WebP with VP8X chunk type."""
        webp_vp8x = b"RIFF" + b"\x00\x00\x00\x00" + b"WEBPVP8X" + b"\x00" * 100
        assert validate_magic_bytes(webp_vp8x, "image/webp") is True

    def test_invalid_jpeg_bytes(self):
        """Should return False for invalid JPEG magic bytes."""
        assert validate_magic_bytes(INVALID_JPEG_BYTES, "image/jpeg") is False

    def test_invalid_webp_missing_webp_signature(self):
        """Should return False for WebP without WEBP signature."""
        invalid_webp = b"RIFF" + b"\x00\x00\x00\x00" + b"XXXX" + b"\x00" * 100
        assert validate_magic_bytes(invalid_webp, "image/webp") is False

    def test_invalid_webp_wrong_chunk_type(self):
        """Should return False for WebP with invalid chunk type."""
        invalid_webp = b"RIFF" + b"\x00\x00\x00\x00" + b"WEBPXXXX" + b"\x00" * 100
        assert validate_magic_bytes(invalid_webp, "image/webp") is False

    def test_invalid_webp_too_short(self):
        """Should return False for WebP file that's too short."""
        short_webp = b"RIFF\x00\x00"
        assert validate_magic_bytes(short_webp, "image/webp") is False

    def test_spoofed_content_type(self):
        """Should return False when PNG bytes are claimed to be JPEG."""
        assert validate_magic_bytes(VALID_PNG_BYTES, "image/jpeg") is False

    def test_unknown_content_type(self):
        """Should return False for unknown content type."""
        assert validate_magic_bytes(VALID_JPEG_BYTES, "image/gif") is False


# ============== StorageService Configuration Tests ==============

class TestStorageServiceConfiguration:
    """Test StorageService initialization and configuration."""

    def test_is_configured_returns_true_when_all_settings_present(self):
        """Should return True when all S3 settings are configured."""
        with patch("app.services.storage.get_settings") as mock_get_settings:
            mock_get_settings.return_value = create_mock_settings()
            service = StorageService()
            assert service.is_configured is True

    def test_is_configured_returns_false_when_endpoint_missing(self):
        """Should return False when endpoint URL is missing."""
        with patch("app.services.storage.get_settings") as mock_get_settings:
            mock_get_settings.return_value = create_mock_settings(s3_endpoint_url=None)
            service = StorageService()
            assert service.is_configured is False

    def test_is_configured_returns_false_when_access_key_missing(self):
        """Should return False when access key is missing."""
        with patch("app.services.storage.get_settings") as mock_get_settings:
            mock_get_settings.return_value = create_mock_settings(s3_access_key_id=None)
            service = StorageService()
            assert service.is_configured is False

    def test_is_configured_returns_false_when_secret_key_missing(self):
        """Should return False when secret key is missing."""
        with patch("app.services.storage.get_settings") as mock_get_settings:
            mock_get_settings.return_value = create_mock_settings(s3_secret_access_key=None)
            service = StorageService()
            assert service.is_configured is False

    def test_is_configured_returns_false_when_public_url_missing(self):
        """Should return False when public URL is missing."""
        with patch("app.services.storage.get_settings") as mock_get_settings:
            mock_get_settings.return_value = create_mock_settings(s3_public_url=None)
            service = StorageService()
            assert service.is_configured is False

    @patch("app.services.storage.boto3.client")
    def test_client_property_creates_boto3_client_when_configured(self, mock_boto3_client):
        """Should create boto3 client with correct parameters when configured."""
        with patch("app.services.storage.get_settings") as mock_get_settings:
            mock_get_settings.return_value = create_mock_settings()
            service = StorageService()

            # Access client property
            client = service.client

            # Verify boto3.client was called with correct parameters
            mock_boto3_client.assert_called_once_with(
                "s3",
                endpoint_url=TEST_ENDPOINT,
                aws_access_key_id=TEST_ACCESS_KEY,
                aws_secret_access_key=TEST_SECRET_KEY,
            )
            assert client == mock_boto3_client.return_value

    def test_client_property_raises_exception_when_not_configured(self):
        """Should raise HTTPException 503 when accessing client while not configured."""
        with patch("app.services.storage.get_settings") as mock_get_settings:
            mock_get_settings.return_value = create_mock_settings(s3_endpoint_url=None)
            service = StorageService()

            with pytest.raises(HTTPException) as exc_info:
                _ = service.client

            assert exc_info.value.status_code == 503
            assert "Storage service not configured" in exc_info.value.detail

    @patch("app.services.storage.boto3.client")
    def test_client_property_uses_lazy_initialization(self, mock_boto3_client):
        """Should only create boto3 client once (lazy initialization)."""
        with patch("app.services.storage.get_settings") as mock_get_settings:
            mock_get_settings.return_value = create_mock_settings()
            service = StorageService()

            # Access client multiple times
            _ = service.client
            _ = service.client
            _ = service.client

            # Verify boto3.client was only called once
            assert mock_boto3_client.call_count == 1


# ============== StorageService.upload_image Tests ==============

class TestStorageServiceUploadImage:
    """Test StorageService.upload_image method."""

    @pytest.mark.asyncio
    @patch("app.services.storage.boto3.client")
    async def test_successful_upload_jpeg(self, mock_boto3_client):
        """Should successfully upload a valid JPEG image."""
        # Setup
        with patch("app.services.storage.get_settings") as mock_get_settings:
            mock_get_settings.return_value = create_mock_settings()
            service = StorageService()

            mock_s3_client = MagicMock()
            mock_boto3_client.return_value = mock_s3_client

            upload_file = create_mock_upload_file(
                filename="test.jpg",
                content_type="image/jpeg",
                content=VALID_JPEG_BYTES,
            )

            # Execute
            url = await service.upload_image(upload_file, "pet-photo", TEST_ORG_ID)

            # Assert
            assert url.startswith(f"{TEST_PUBLIC_URL}/pets/{TEST_ORG_ID}/")
            assert url.endswith(".jpg")
            mock_s3_client.put_object.assert_called_once()

            # Verify put_object was called with correct parameters
            call_kwargs = mock_s3_client.put_object.call_args[1]
            assert call_kwargs["Bucket"] == TEST_BUCKET
            assert call_kwargs["Key"].startswith(f"pets/{TEST_ORG_ID}/")
            assert call_kwargs["Key"].endswith(".jpg")
            assert call_kwargs["Body"] == VALID_JPEG_BYTES
            assert call_kwargs["ContentType"] == "image/jpeg"

    @pytest.mark.asyncio
    @patch("app.services.storage.boto3.client")
    async def test_successful_upload_png(self, mock_boto3_client):
        """Should successfully upload a valid PNG image."""
        with patch("app.services.storage.get_settings") as mock_get_settings:
            mock_get_settings.return_value = create_mock_settings()
            service = StorageService()

            mock_s3_client = MagicMock()
            mock_boto3_client.return_value = mock_s3_client

            upload_file = create_mock_upload_file(
                filename="test.png",
                content_type="image/png",
                content=VALID_PNG_BYTES,
            )

            url = await service.upload_image(upload_file, "food-photo", TEST_ORG_ID)

            assert url.startswith(f"{TEST_PUBLIC_URL}/foods/{TEST_ORG_ID}/")
            assert url.endswith(".png")

    @pytest.mark.asyncio
    @patch("app.services.storage.boto3.client")
    async def test_successful_upload_webp(self, mock_boto3_client):
        """Should successfully upload a valid WebP image."""
        with patch("app.services.storage.get_settings") as mock_get_settings:
            mock_get_settings.return_value = create_mock_settings()
            service = StorageService()

            mock_s3_client = MagicMock()
            mock_boto3_client.return_value = mock_s3_client

            upload_file = create_mock_upload_file(
                filename="test.webp",
                content_type="image/webp",
                content=VALID_WEBP_BYTES,
            )

            url = await service.upload_image(upload_file, "medicine-photo", TEST_ORG_ID)

            assert url.startswith(f"{TEST_PUBLIC_URL}/medicines/{TEST_ORG_ID}/")
            assert url.endswith(".webp")

    @pytest.mark.asyncio
    @patch("app.services.storage.boto3.client")
    async def test_upload_health_event_photo(self, mock_boto3_client):
        """Should upload to health-events folder for health-event-photo type."""
        with patch("app.services.storage.get_settings") as mock_get_settings:
            mock_get_settings.return_value = create_mock_settings()
            service = StorageService()

            mock_s3_client = MagicMock()
            mock_boto3_client.return_value = mock_s3_client

            upload_file = create_mock_upload_file()

            url = await service.upload_image(upload_file, "health-event-photo", TEST_ORG_ID)

            assert url.startswith(f"{TEST_PUBLIC_URL}/health-events/{TEST_ORG_ID}/")

    @pytest.mark.asyncio
    async def test_upload_invalid_upload_type(self):
        """Should raise HTTPException 400 for invalid upload type."""
        with patch("app.services.storage.get_settings") as mock_get_settings:
            mock_get_settings.return_value = create_mock_settings()
            service = StorageService()

            upload_file = create_mock_upload_file()

            with pytest.raises(HTTPException) as exc_info:
                await service.upload_image(upload_file, "invalid-type", TEST_ORG_ID)

            assert exc_info.value.status_code == 400
            assert "Invalid upload type" in exc_info.value.detail
            assert "pet-photo" in exc_info.value.detail  # Should list valid types

    @pytest.mark.asyncio
    async def test_upload_invalid_content_type(self):
        """Should raise HTTPException 400 for unsupported content type."""
        with patch("app.services.storage.get_settings") as mock_get_settings:
            mock_get_settings.return_value = create_mock_settings()
            service = StorageService()

            upload_file = create_mock_upload_file(content_type="image/gif")

            with pytest.raises(HTTPException) as exc_info:
                await service.upload_image(upload_file, "pet-photo", TEST_ORG_ID)

            assert exc_info.value.status_code == 400
            assert "Invalid file type" in exc_info.value.detail
            assert "JPEG, PNG, WebP" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_upload_file_too_large(self):
        """Should raise HTTPException 400 when file exceeds size limit."""
        with patch("app.services.storage.get_settings") as mock_get_settings:
            mock_get_settings.return_value = create_mock_settings()
            service = StorageService()

            upload_file = create_mock_upload_file(content=LARGE_FILE)

            with pytest.raises(HTTPException) as exc_info:
                await service.upload_image(upload_file, "pet-photo", TEST_ORG_ID)

            assert exc_info.value.status_code == 400
            assert "File too large" in exc_info.value.detail
            assert "5MB" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_upload_file_at_size_boundary(self):
        """Should accept file exactly at MAX_FILE_SIZE."""
        with patch("app.services.storage.get_settings") as mock_get_settings, \
             patch("app.services.storage.boto3.client") as mock_boto3_client:
            mock_get_settings.return_value = create_mock_settings()
            service = StorageService()

            mock_s3_client = MagicMock()
            mock_boto3_client.return_value = mock_s3_client

            # Create file exactly at limit
            boundary_content = VALID_JPEG_BYTES[:20] + b"\x00" * (MAX_FILE_SIZE - 20)
            upload_file = create_mock_upload_file(content=boundary_content)

            # Should not raise
            url = await service.upload_image(upload_file, "pet-photo", TEST_ORG_ID)
            assert url is not None

    @pytest.mark.asyncio
    async def test_upload_invalid_magic_bytes(self):
        """Should raise HTTPException 400 when magic bytes don't match content type."""
        with patch("app.services.storage.get_settings") as mock_get_settings:
            mock_get_settings.return_value = create_mock_settings()
            service = StorageService()

            # Claim it's JPEG but use PNG magic bytes (spoofing)
            upload_file = create_mock_upload_file(
                content_type="image/jpeg",
                content=VALID_PNG_BYTES,
            )

            with pytest.raises(HTTPException) as exc_info:
                await service.upload_image(upload_file, "pet-photo", TEST_ORG_ID)

            assert exc_info.value.status_code == 400
            assert "File content does not match declared type" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("app.services.storage.boto3.client")
    async def test_upload_s3_client_error(self, mock_boto3_client):
        """Should raise HTTPException 500 when S3 upload fails."""
        with patch("app.services.storage.get_settings") as mock_get_settings:
            mock_get_settings.return_value = create_mock_settings()
            service = StorageService()

            mock_s3_client = MagicMock()
            mock_s3_client.put_object.side_effect = ClientError(
                {"Error": {"Code": "NoSuchBucket", "Message": "Bucket not found"}},
                "PutObject"
            )
            mock_boto3_client.return_value = mock_s3_client

            upload_file = create_mock_upload_file()

            with pytest.raises(HTTPException) as exc_info:
                await service.upload_image(upload_file, "pet-photo", TEST_ORG_ID)

            assert exc_info.value.status_code == 500
            assert "Failed to upload image" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("app.services.storage.boto3.client")
    async def test_upload_generates_unique_filenames(self, mock_boto3_client):
        """Should generate unique filenames for each upload using UUID."""
        with patch("app.services.storage.get_settings") as mock_get_settings:
            mock_get_settings.return_value = create_mock_settings()
            service = StorageService()

            mock_s3_client = MagicMock()
            mock_boto3_client.return_value = mock_s3_client

            upload_file1 = create_mock_upload_file()
            upload_file2 = create_mock_upload_file()

            url1 = await service.upload_image(upload_file1, "pet-photo", TEST_ORG_ID)
            url2 = await service.upload_image(upload_file2, "pet-photo", TEST_ORG_ID)

            # URLs should be different (different UUIDs)
            assert url1 != url2

            # Both should be in same folder
            assert url1.startswith(f"{TEST_PUBLIC_URL}/pets/{TEST_ORG_ID}/")
            assert url2.startswith(f"{TEST_PUBLIC_URL}/pets/{TEST_ORG_ID}/")


# ============== StorageService.delete_image Tests ==============

class TestStorageServiceDeleteImage:
    """Test StorageService.delete_image method."""

    @pytest.mark.asyncio
    @patch("app.services.storage.boto3.client")
    async def test_successful_delete(self, mock_boto3_client):
        """Should successfully delete an image from R2."""
        with patch("app.services.storage.get_settings") as mock_get_settings:
            mock_get_settings.return_value = create_mock_settings()
            service = StorageService()

            mock_s3_client = MagicMock()
            mock_boto3_client.return_value = mock_s3_client

            url = f"{TEST_PUBLIC_URL}/pets/{TEST_ORG_ID}/12345.jpg"

            result = await service.delete_image(url)

            assert result is True
            mock_s3_client.delete_object.assert_called_once_with(
                Bucket=TEST_BUCKET,
                Key=f"pets/{TEST_ORG_ID}/12345.jpg",
            )

    @pytest.mark.asyncio
    @patch("app.services.storage.boto3.client")
    async def test_delete_extracts_correct_key_from_url(self, mock_boto3_client):
        """Should correctly extract S3 key from public URL."""
        with patch("app.services.storage.get_settings") as mock_get_settings:
            mock_get_settings.return_value = create_mock_settings()
            service = StorageService()

            mock_s3_client = MagicMock()
            mock_boto3_client.return_value = mock_s3_client

            url = f"{TEST_PUBLIC_URL}/foods/{TEST_ORG_ID}/abc-def-123.png"

            await service.delete_image(url)

            call_kwargs = mock_s3_client.delete_object.call_args[1]
            assert call_kwargs["Key"] == f"foods/{TEST_ORG_ID}/abc-def-123.png"

    @pytest.mark.asyncio
    async def test_delete_returns_false_when_not_configured(self):
        """Should return False when storage is not configured."""
        with patch("app.services.storage.get_settings") as mock_get_settings:
            mock_get_settings.return_value = create_mock_settings(s3_endpoint_url=None)
            service = StorageService()

            url = f"{TEST_PUBLIC_URL}/pets/{TEST_ORG_ID}/12345.jpg"

            result = await service.delete_image(url)

            assert result is False

    @pytest.mark.asyncio
    async def test_delete_returns_false_for_non_matching_url(self):
        """Should return False when URL doesn't match our storage domain."""
        with patch("app.services.storage.get_settings") as mock_get_settings:
            mock_get_settings.return_value = create_mock_settings()
            service = StorageService()

            # URL from different CDN
            url = "https://other-cdn.com/pets/12345.jpg"

            result = await service.delete_image(url)

            assert result is False

    @pytest.mark.asyncio
    @patch("app.services.storage.boto3.client")
    async def test_delete_returns_false_on_client_error(self, mock_boto3_client):
        """Should return False when S3 delete operation fails."""
        with patch("app.services.storage.get_settings") as mock_get_settings:
            mock_get_settings.return_value = create_mock_settings()
            service = StorageService()

            mock_s3_client = MagicMock()
            mock_s3_client.delete_object.side_effect = ClientError(
                {"Error": {"Code": "NoSuchKey", "Message": "Key not found"}},
                "DeleteObject"
            )
            mock_boto3_client.return_value = mock_s3_client

            url = f"{TEST_PUBLIC_URL}/pets/{TEST_ORG_ID}/12345.jpg"

            result = await service.delete_image(url)

            assert result is False

    @pytest.mark.asyncio
    @patch("app.services.storage.boto3.client")
    async def test_delete_handles_nested_paths(self, mock_boto3_client):
        """Should correctly handle URLs with nested folder paths."""
        with patch("app.services.storage.get_settings") as mock_get_settings:
            mock_get_settings.return_value = create_mock_settings()
            service = StorageService()

            mock_s3_client = MagicMock()
            mock_boto3_client.return_value = mock_s3_client

            url = f"{TEST_PUBLIC_URL}/health-events/{TEST_ORG_ID}/subfolder/image.jpg"

            await service.delete_image(url)

            call_kwargs = mock_s3_client.delete_object.call_args[1]
            assert call_kwargs["Key"] == f"health-events/{TEST_ORG_ID}/subfolder/image.jpg"


# ============== Edge Cases and Integration Tests ==============

class TestStorageServiceEdgeCases:
    """Test edge cases and integration scenarios."""

    @pytest.mark.asyncio
    async def test_empty_file(self):
        """Should reject empty files."""
        with patch("app.services.storage.get_settings") as mock_get_settings:
            mock_get_settings.return_value = create_mock_settings()
            service = StorageService()

            upload_file = create_mock_upload_file(content=b"")

            with pytest.raises(HTTPException) as exc_info:
                await service.upload_image(upload_file, "pet-photo", TEST_ORG_ID)

            # Should fail magic bytes validation
            assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_file_with_only_magic_bytes(self):
        """Should accept file with only magic bytes (minimal valid file)."""
        with patch("app.services.storage.get_settings") as mock_get_settings, \
             patch("app.services.storage.boto3.client") as mock_boto3_client:
            mock_get_settings.return_value = create_mock_settings()
            service = StorageService()

            mock_s3_client = MagicMock()
            mock_boto3_client.return_value = mock_s3_client

            # Minimal JPEG
            minimal_jpeg = b"\xff\xd8\xff\xe0"
            upload_file = create_mock_upload_file(content=minimal_jpeg)

            url = await service.upload_image(upload_file, "pet-photo", TEST_ORG_ID)
            assert url is not None

    @pytest.mark.asyncio
    @patch("app.services.storage.boto3.client")
    async def test_concurrent_uploads_use_different_uuids(self, mock_boto3_client):
        """Should handle concurrent uploads with different UUIDs."""
        with patch("app.services.storage.get_settings") as mock_get_settings:
            mock_get_settings.return_value = create_mock_settings()
            service = StorageService()

            mock_s3_client = MagicMock()
            mock_boto3_client.return_value = mock_s3_client

            upload_file1 = create_mock_upload_file()
            upload_file2 = create_mock_upload_file()
            upload_file3 = create_mock_upload_file()

            # Upload concurrently
            results = await asyncio.gather(
                service.upload_image(upload_file1, "pet-photo", TEST_ORG_ID),
                service.upload_image(upload_file2, "pet-photo", TEST_ORG_ID),
                service.upload_image(upload_file3, "pet-photo", TEST_ORG_ID),
            )

            # All should succeed
            assert len(results) == 3
            assert all(url.startswith(TEST_PUBLIC_URL) for url in results)

            # All should have unique URLs
            assert len(set(results)) == 3

    @pytest.mark.asyncio
    async def test_different_orgs_use_different_folders(self):
        """Should upload files for different orgs to separate folders."""
        with patch("app.services.storage.get_settings") as mock_get_settings, \
             patch("app.services.storage.boto3.client") as mock_boto3_client:
            mock_get_settings.return_value = create_mock_settings()
            service = StorageService()

            mock_s3_client = MagicMock()
            mock_boto3_client.return_value = mock_s3_client

            org_id_1 = str(uuid4())
            org_id_2 = str(uuid4())

            upload_file1 = create_mock_upload_file()
            upload_file2 = create_mock_upload_file()

            url1 = await service.upload_image(upload_file1, "pet-photo", org_id_1)
            url2 = await service.upload_image(upload_file2, "pet-photo", org_id_2)

            # Should be in different org folders
            assert f"/pets/{org_id_1}/" in url1
            assert f"/pets/{org_id_2}/" in url2
            assert url1 != url2

    def test_upload_folders_constant_completeness(self):
        """Should verify all expected upload types are defined."""
        expected_types = ["pet-photo", "food-photo", "medicine-photo", "health-event-photo"]
        for upload_type in expected_types:
            assert upload_type in UPLOAD_FOLDERS, f"Missing upload type: {upload_type}"

    def test_allowed_mime_types_constant_completeness(self):
        """Should verify all expected MIME types are defined."""
        expected_types = ["image/jpeg", "image/png", "image/webp"]
        for mime_type in expected_types:
            assert mime_type in ALLOWED_MIME_TYPES, f"Missing MIME type: {mime_type}"

    def test_singleton_instance_exists(self):
        """Should verify storage_service singleton exists."""
        assert storage_service is not None
        assert isinstance(storage_service, StorageService)
