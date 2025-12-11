"""
File upload endpoints for images (pets, profiles, food, medicine, etc.)
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.core.security import get_current_user_id
from app.models.user import FamilyMember
from app.services.storage import storage_service

router = APIRouter()


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
    upload_type: str,
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
        upload_type=upload_type,
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
    # Verify user is in a family (basic auth check)
    await get_user_org_id(db, user_id)

    # Delete from R2
    success = await storage_service.delete_image(url)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found or could not be deleted"
        )

    return {"success": True}
