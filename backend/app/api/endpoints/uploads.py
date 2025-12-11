"""
File upload endpoints for images (pets, profiles, food, medicine, etc.)
"""
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.core.security import get_current_user_id
from app.models.user import FamilyMember
from app.services.storage import storage_service

router = APIRouter()


class UploadType(str, Enum):
    """Valid upload types for image uploads."""
    PET_PHOTO = "pet-photo"
    FOOD_PHOTO = "food-photo"
    MEDICINE_PHOTO = "medicine-photo"


async def get_user_org_id(db: AsyncSession, user_id: str) -> str:
    """Get the user's family (org) ID from their membership."""
    query = select(FamilyMember.family_id).where(FamilyMember.user_id == user_id)
    result = await db.execute(query)
    family_id = result.scalar_one_or_none()

    if not family_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User must be a member of a family to upload images"
        )

    return str(family_id)


@router.post("/{upload_type}")
async def upload_image(
    upload_type: UploadType,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """Upload an image file.

    Args:
        upload_type: Type of upload (pet-photo, profile-photo, food-photo, medicine-photo)
        file: The image file to upload

    Returns:
        JSON with the public URL of the uploaded image
    """
    # Get user's org_id from their family membership
    org_id = await get_user_org_id(db, user_id)

    # Upload to R2
    url = await storage_service.upload_image(
        file=file,
        upload_type=upload_type.value,
        org_id=org_id,
    )

    return {"url": url}


@router.delete("")
async def delete_image(
    url: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """Delete an uploaded image.

    Args:
        url: The public URL of the image to delete

    Returns:
        JSON with success status
    """
    # Get user's org_id
    user_org_id = await get_user_org_id(db, user_id)

    # Validate URL belongs to user's family by checking org_id in path
    # URL format: {public_url}/{folder}/{org_id}/{file_id}.{extension}
    if not storage_service.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Storage service not configured"
        )

    public_url_base = storage_service.settings.s3_public_url
    if not url.startswith(public_url_base):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image URL"
        )

    # Extract path: folder/org_id/filename
    path = url.replace(f"{public_url_base}/", "")
    path_parts = path.split("/")

    # Validate path format: folder/org_id/filename
    if len(path_parts) != 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image URL format"
        )

    folder, url_org_id, filename = path_parts

    # Verify the org_id in URL matches user's org_id (security check)
    if url_org_id != user_org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this image"
        )

    # Delete from R2
    success = await storage_service.delete_image(url)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found or could not be deleted"
        )

    return {"success": True}
