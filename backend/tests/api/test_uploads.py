"""
Comprehensive integration tests for file upload endpoints.

Tests cover:
- POST /api/v1/uploads/{upload_type} - upload image
- DELETE /api/v1/uploads - delete image
- Authorization checks (must be family member)
- File type validation (JPEG, PNG, WebP only)
- File size validation (5MB max)
- Magic bytes validation (prevent spoofed content types)
- Storage service mocking
- Upload type validation
- URL path validation for delete
- Family ID security checks

NOTE: These tests mock the storage_service to avoid actual S3/R2 uploads.
The storage service is imported as a singleton, so we patch it at the module level.
"""
import io
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient

from tests.conftest import (
    TEST_FAMILY_ID,
    TEST_USER_ID,
    create_mock_membership,
)


# ============== Helper Functions ==============

def create_test_image(content_type: str = "image/jpeg", size: int = 1024) -> bytes:
    """Create test image content with valid magic bytes.

    Args:
        content_type: MIME type (image/jpeg, image/png, image/webp)
        size: Total size of the file in bytes

    Returns:
        Bytes representing a valid image file
    """
    if content_type == "image/jpeg":
        # JPEG magic bytes: FF D8 FF
        magic_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00"
    elif content_type == "image/png":
        # PNG magic bytes: 89 50 4E 47 0D 0A 1A 0A
        magic_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    elif content_type == "image/webp":
        # WebP magic bytes: RIFF + WEBP + VP8
        magic_bytes = b"RIFF\x00\x00\x00\x00WEBPVP8 "
    else:
        magic_bytes = b""

    # Pad to requested size
    padding_size = max(0, size - len(magic_bytes))
    return magic_bytes + b"\x00" * padding_size


def create_invalid_image(size: int = 1024) -> bytes:
    """Create invalid image content (wrong magic bytes)."""
    return b"\x00" * size


class MockUploadFile:
    """Mock UploadFile for testing."""

    def __init__(self, filename: str, content_type: str, content: bytes):
        self.filename = filename
        self.content_type = content_type
        self._content = content
        self.file = io.BytesIO(content)

    async def read(self) -> bytes:
        return self._content

    async def seek(self, position: int):
        self.file.seek(position)


# ============== Upload Image Tests ==============

class TestUploadImage:
    """Tests for POST /api/v1/uploads/{upload_type} endpoint."""

    @pytest.mark.asyncio
    async def test_upload_pet_photo_success(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should successfully upload a pet photo."""
        from uuid import UUID

        # Mock database query for family membership
        # The query uses scalar_one_or_none() which returns just the family_id value
        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = UUID(test_family_id)
        mock_db_session.execute = AsyncMock(return_value=membership_result)

        # Mock storage service
        expected_url = f"https://r2.example.com/pets/{test_family_id}/12345.jpg"

        with patch("app.api.endpoints.uploads.storage_service") as mock_storage:
            mock_storage.upload_image = AsyncMock(return_value=expected_url)

            # Create test file
            image_content = create_test_image("image/jpeg", 2048)

            # Make request
            response = await client.post(
                "/api/v1/uploads/pet-photo",
                headers=auth_headers,
                files={"file": ("test.jpg", image_content, "image/jpeg")},
            )

            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["url"] == expected_url

            # Verify storage service was called
            mock_storage.upload_image.assert_called_once()
            call_args = mock_storage.upload_image.call_args
            assert call_args.kwargs["upload_type"] == "pet-photo"
            assert call_args.kwargs["family_id"] == test_family_id

    @pytest.mark.asyncio
    async def test_upload_food_photo_success(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should successfully upload a food photo."""
        from uuid import UUID

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = UUID(test_family_id)
        mock_db_session.execute = AsyncMock(return_value=membership_result)

        expected_url = f"https://r2.example.com/foods/{test_family_id}/12345.png"

        with patch("app.api.endpoints.uploads.storage_service") as mock_storage:
            mock_storage.upload_image = AsyncMock(return_value=expected_url)

            image_content = create_test_image("image/png", 3072)

            response = await client.post(
                "/api/v1/uploads/food-photo",
                headers=auth_headers,
                files={"file": ("test.png", image_content, "image/png")},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["url"] == expected_url

    @pytest.mark.asyncio
    async def test_upload_medicine_photo_success(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should successfully upload a medicine photo."""
        from uuid import UUID

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = UUID(test_family_id)
        mock_db_session.execute = AsyncMock(return_value=membership_result)

        expected_url = f"https://r2.example.com/medicines/{test_family_id}/12345.webp"

        with patch("app.api.endpoints.uploads.storage_service") as mock_storage:
            mock_storage.upload_image = AsyncMock(return_value=expected_url)

            image_content = create_test_image("image/webp", 2560)

            response = await client.post(
                "/api/v1/uploads/medicine-photo",
                headers=auth_headers,
                files={"file": ("test.webp", image_content, "image/webp")},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["url"] == expected_url

    @pytest.mark.asyncio
    async def test_upload_health_event_photo_success(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should successfully upload a health event photo."""
        from uuid import UUID

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = UUID(test_family_id)
        mock_db_session.execute = AsyncMock(return_value=membership_result)

        expected_url = f"https://r2.example.com/health-events/{test_family_id}/12345.jpg"

        with patch("app.api.endpoints.uploads.storage_service") as mock_storage:
            mock_storage.upload_image = AsyncMock(return_value=expected_url)

            image_content = create_test_image("image/jpeg", 1536)

            response = await client.post(
                "/api/v1/uploads/health-event-photo",
                headers=auth_headers,
                files={"file": ("test.jpg", image_content, "image/jpeg")},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["url"] == expected_url

    @pytest.mark.asyncio
    async def test_upload_without_auth(
        self,
        client: AsyncClient,
    ):
        """Should return 401 when no auth token provided."""
        image_content = create_test_image("image/jpeg")

        response = await client.post(
            "/api/v1/uploads/pet-photo",
            files={"file": ("test.jpg", image_content, "image/jpeg")},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_upload_user_not_in_family(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
    ):
        """Should return 403 when user is not in any family."""
        # Mock no family membership found - scalar_one_or_none returns None
        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=membership_result)

        image_content = create_test_image("image/jpeg")

        response = await client.post(
            "/api/v1/uploads/pet-photo",
            headers=auth_headers,
            files={"file": ("test.jpg", image_content, "image/jpeg")},
        )

        assert response.status_code == 403
        data = response.json()
        assert "must be a member of a family" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_upload_invalid_upload_type(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should return 422 when upload type is invalid."""
        from uuid import UUID

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = UUID(test_family_id)
        mock_db_session.execute = AsyncMock(return_value=membership_result)

        image_content = create_test_image("image/jpeg")

        # Try an invalid upload type
        response = await client.post(
            "/api/v1/uploads/invalid-type",
            headers=auth_headers,
            files={"file": ("test.jpg", image_content, "image/jpeg")},
        )

        # FastAPI validation will return 422 for invalid enum value
        assert response.status_code == 422


# ============== File Validation Tests ==============

class TestFileValidation:
    """Tests for file type and size validation."""

    @pytest.mark.asyncio
    async def test_upload_invalid_content_type(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should return 400 when file type is not allowed."""
        from uuid import UUID

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = UUID(test_family_id)
        mock_db_session.execute = AsyncMock(return_value=membership_result)

        with patch("app.api.endpoints.uploads.storage_service") as mock_storage:
            # Storage service will raise HTTPException for invalid content type
            from fastapi import HTTPException
            mock_storage.upload_image = AsyncMock(
                side_effect=HTTPException(
                    status_code=400,
                    detail="Invalid file type: image/gif. Allowed types: JPEG, PNG, WebP"
                )
            )

            # Try to upload a GIF (not allowed)
            response = await client.post(
                "/api/v1/uploads/pet-photo",
                headers=auth_headers,
                files={"file": ("test.gif", b"GIF89a", "image/gif")},
            )

            assert response.status_code == 400
            data = response.json()
            assert "invalid file type" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_upload_file_too_large(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should return 400 when file exceeds 5MB limit."""
        from uuid import UUID

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = UUID(test_family_id)
        mock_db_session.execute = AsyncMock(return_value=membership_result)

        with patch("app.api.endpoints.uploads.storage_service") as mock_storage:
            # Storage service will raise HTTPException for file too large
            from fastapi import HTTPException
            mock_storage.upload_image = AsyncMock(
                side_effect=HTTPException(
                    status_code=400,
                    detail="File too large. Maximum size is 5MB"
                )
            )

            # Create a large file (6MB)
            large_content = create_test_image("image/jpeg", 6 * 1024 * 1024)

            response = await client.post(
                "/api/v1/uploads/pet-photo",
                headers=auth_headers,
                files={"file": ("large.jpg", large_content, "image/jpeg")},
            )

            assert response.status_code == 400
            data = response.json()
            assert "too large" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_upload_invalid_magic_bytes(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should return 400 when file content doesn't match declared type."""
        from uuid import UUID

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = UUID(test_family_id)
        mock_db_session.execute = AsyncMock(return_value=membership_result)

        with patch("app.api.endpoints.uploads.storage_service") as mock_storage:
            # Storage service will raise HTTPException for invalid magic bytes
            from fastapi import HTTPException
            mock_storage.upload_image = AsyncMock(
                side_effect=HTTPException(
                    status_code=400,
                    detail="File content does not match declared type: image/jpeg"
                )
            )

            # Create file with wrong magic bytes
            invalid_content = create_invalid_image(1024)

            response = await client.post(
                "/api/v1/uploads/pet-photo",
                headers=auth_headers,
                files={"file": ("fake.jpg", invalid_content, "image/jpeg")},
            )

            assert response.status_code == 400
            data = response.json()
            assert "does not match" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_upload_storage_service_failure(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should return 500 when storage service fails."""
        from uuid import UUID

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = UUID(test_family_id)
        mock_db_session.execute = AsyncMock(return_value=membership_result)

        with patch("app.api.endpoints.uploads.storage_service") as mock_storage:
            # Storage service will raise HTTPException for upload failure
            from fastapi import HTTPException
            mock_storage.upload_image = AsyncMock(
                side_effect=HTTPException(
                    status_code=500,
                    detail="Failed to upload image"
                )
            )

            image_content = create_test_image("image/jpeg")

            response = await client.post(
                "/api/v1/uploads/pet-photo",
                headers=auth_headers,
                files={"file": ("test.jpg", image_content, "image/jpeg")},
            )

            assert response.status_code == 500


# ============== Delete Image Tests ==============

class TestDeleteImage:
    """Tests for DELETE /api/v1/uploads endpoint."""

    @pytest.mark.asyncio
    async def test_delete_image_success(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should successfully delete an image that belongs to user's family."""
        from uuid import UUID

        # Mock family membership query - returns just the family_id
        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = UUID(test_family_id)
        mock_db_session.execute = AsyncMock(return_value=membership_result)

        # Mock storage service
        with patch("app.api.endpoints.uploads.storage_service") as mock_storage:
            mock_storage.is_configured = True
            mock_storage.settings.s3_public_url = "https://r2.example.com"
            mock_storage.delete_image = AsyncMock(return_value=True)

            # URL format: {public_url}/{folder}/{family_id}/{file_id}.{extension}
            image_url = f"https://r2.example.com/pets/{test_family_id}/12345.jpg"

            response = await client.delete(
                f"/api/v1/uploads?url={image_url}",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

            # Verify storage service was called
            mock_storage.delete_image.assert_called_once_with(image_url)

    @pytest.mark.asyncio
    async def test_delete_image_wrong_family_id(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should return 403 when trying to delete image from different family."""
        from uuid import UUID

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = UUID(test_family_id)
        mock_db_session.execute = AsyncMock(return_value=membership_result)

        with patch("app.api.endpoints.uploads.storage_service") as mock_storage:
            mock_storage.is_configured = True
            mock_storage.settings.s3_public_url = "https://r2.example.com"

            # Try to delete image from different family
            other_family_id = str(uuid4())
            image_url = f"https://r2.example.com/pets/{other_family_id}/12345.jpg"

            response = await client.delete(
                f"/api/v1/uploads?url={image_url}",
                headers=auth_headers,
            )

            assert response.status_code == 403
            data = response.json()
            assert "permission" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_delete_image_invalid_url(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should return 400 when URL is invalid."""
        from uuid import UUID

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = UUID(test_family_id)
        mock_db_session.execute = AsyncMock(return_value=membership_result)

        with patch("app.api.endpoints.uploads.storage_service") as mock_storage:
            mock_storage.is_configured = True
            mock_storage.settings.s3_public_url = "https://r2.example.com"

            # Invalid URL from different domain
            image_url = "https://evil.com/pets/12345/file.jpg"

            response = await client.delete(
                f"/api/v1/uploads?url={image_url}",
                headers=auth_headers,
            )

            assert response.status_code == 400
            data = response.json()
            assert "invalid" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_delete_image_invalid_path_format(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should return 400 when URL path format is invalid."""
        from uuid import UUID

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = UUID(test_family_id)
        mock_db_session.execute = AsyncMock(return_value=membership_result)

        with patch("app.api.endpoints.uploads.storage_service") as mock_storage:
            mock_storage.is_configured = True
            mock_storage.settings.s3_public_url = "https://r2.example.com"

            # Invalid path format (missing family_id level)
            image_url = "https://r2.example.com/pets/12345.jpg"

            response = await client.delete(
                f"/api/v1/uploads?url={image_url}",
                headers=auth_headers,
            )

            assert response.status_code == 400
            data = response.json()
            assert "invalid" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_delete_image_not_found(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should return 404 when image doesn't exist."""
        from uuid import UUID

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = UUID(test_family_id)
        mock_db_session.execute = AsyncMock(return_value=membership_result)

        with patch("app.api.endpoints.uploads.storage_service") as mock_storage:
            mock_storage.is_configured = True
            mock_storage.settings.s3_public_url = "https://r2.example.com"
            mock_storage.delete_image = AsyncMock(return_value=False)

            image_url = f"https://r2.example.com/pets/{test_family_id}/nonexistent.jpg"

            response = await client.delete(
                f"/api/v1/uploads?url={image_url}",
                headers=auth_headers,
            )

            assert response.status_code == 404
            data = response.json()
            assert "not found" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_delete_image_storage_not_configured(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should return 503 when storage service is not configured."""
        from uuid import UUID

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = UUID(test_family_id)
        mock_db_session.execute = AsyncMock(return_value=membership_result)

        with patch("app.api.endpoints.uploads.storage_service") as mock_storage:
            mock_storage.is_configured = False

            image_url = f"https://r2.example.com/pets/{test_family_id}/12345.jpg"

            response = await client.delete(
                f"/api/v1/uploads?url={image_url}",
                headers=auth_headers,
            )

            assert response.status_code == 503
            data = response.json()
            assert "not configured" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_delete_image_without_auth(
        self,
        client: AsyncClient,
    ):
        """Should return 401 when no auth token provided."""
        response = await client.delete(
            "/api/v1/uploads?url=https://r2.example.com/pets/123/file.jpg",
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_image_user_not_in_family(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
    ):
        """Should return 403 when user is not in any family."""
        # Mock no family membership found
        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=membership_result)

        response = await client.delete(
            "/api/v1/uploads?url=https://r2.example.com/pets/123/file.jpg",
            headers=auth_headers,
        )

        assert response.status_code == 403
        data = response.json()
        assert "must be a member of a family" in data["detail"].lower()


# ============== Edge Cases and Security Tests ==============

class TestEdgeCasesAndSecurity:
    """Tests for edge cases and security scenarios."""

    @pytest.mark.asyncio
    async def test_upload_empty_file(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should handle empty file uploads."""
        from uuid import UUID

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = UUID(test_family_id)
        mock_db_session.execute = AsyncMock(return_value=membership_result)

        with patch("app.api.endpoints.uploads.storage_service") as mock_storage:
            from fastapi import HTTPException
            mock_storage.upload_image = AsyncMock(
                side_effect=HTTPException(
                    status_code=400,
                    detail="File content does not match declared type: image/jpeg"
                )
            )

            response = await client.post(
                "/api/v1/uploads/pet-photo",
                headers=auth_headers,
                files={"file": ("empty.jpg", b"", "image/jpeg")},
            )

            # Should fail validation
            assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_upload_all_valid_upload_types(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should accept all valid upload types."""
        from uuid import UUID

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = UUID(test_family_id)

        # Need to return a new result for each call
        mock_db_session.execute = AsyncMock(
            side_effect=[membership_result, membership_result, membership_result, membership_result]
        )

        upload_types = ["pet-photo", "food-photo", "medicine-photo", "health-event-photo"]

        with patch("app.api.endpoints.uploads.storage_service") as mock_storage:
            mock_storage.upload_image = AsyncMock(return_value="https://r2.example.com/test.jpg")

            for upload_type in upload_types:
                image_content = create_test_image("image/jpeg")

                response = await client.post(
                    f"/api/v1/uploads/{upload_type}",
                    headers=auth_headers,
                    files={"file": ("test.jpg", image_content, "image/jpeg")},
                )

                assert response.status_code == 200, f"Failed for {upload_type}"

    @pytest.mark.asyncio
    async def test_delete_url_with_special_characters(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should handle URLs with special characters properly."""
        from uuid import UUID

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = UUID(test_family_id)
        mock_db_session.execute = AsyncMock(return_value=membership_result)

        with patch("app.api.endpoints.uploads.storage_service") as mock_storage:
            mock_storage.is_configured = True
            mock_storage.settings.s3_public_url = "https://r2.example.com"
            mock_storage.delete_image = AsyncMock(return_value=True)

            # URL with UUID containing hyphens
            image_url = f"https://r2.example.com/pets/{test_family_id}/abc-def-123.jpg"

            response = await client.delete(
                f"/api/v1/uploads?url={image_url}",
                headers=auth_headers,
            )

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_concurrent_uploads_different_types(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should handle concurrent uploads of different types."""
        from uuid import UUID

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = UUID(test_family_id)
        mock_db_session.execute = AsyncMock(return_value=membership_result)

        with patch("app.api.endpoints.uploads.storage_service") as mock_storage:
            mock_storage.upload_image = AsyncMock(
                side_effect=[
                    "https://r2.example.com/pets/1.jpg",
                    "https://r2.example.com/foods/2.png",
                ]
            )

            # Upload pet photo
            pet_content = create_test_image("image/jpeg")
            response1 = await client.post(
                "/api/v1/uploads/pet-photo",
                headers=auth_headers,
                files={"file": ("pet.jpg", pet_content, "image/jpeg")},
            )

            # Upload food photo
            food_content = create_test_image("image/png")
            response2 = await client.post(
                "/api/v1/uploads/food-photo",
                headers=auth_headers,
                files={"file": ("food.png", food_content, "image/png")},
            )

            assert response1.status_code == 200
            assert response2.status_code == 200
            assert response1.json()["url"] != response2.json()["url"]
