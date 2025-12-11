from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.core.security import get_current_user_id
from app.models.notification import UserDeviceToken, NotificationPreference
from app.schemas.notification import (
    DeviceTokenCreate, DeviceTokenDelete, DeviceTokenResponse,
    NotificationPreferencesUpdate, NotificationPreferencesResponse,
)
from app.services.apns import apns_service

router = APIRouter()


@router.post("/device-token", response_model=DeviceTokenResponse, status_code=status.HTTP_201_CREATED)
async def register_device_token(
    token_in: DeviceTokenCreate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Register or update a device token for push notifications."""
    user_uuid = UUID(user_id)

    # Check if token already exists for this user
    existing = await db.execute(
        select(UserDeviceToken).where(
            and_(
                UserDeviceToken.user_id == user_uuid,
                UserDeviceToken.device_token == token_in.device_token,
            )
        )
    )
    existing_token = existing.scalar_one_or_none()

    if existing_token:
        # Reactivate if it was deactivated
        existing_token.is_active = True
        existing_token.device_name = token_in.device_name or existing_token.device_name
        await db.commit()
        await db.refresh(existing_token)
        return DeviceTokenResponse.model_validate(existing_token)

    # Create new token
    device_token = UserDeviceToken(
        user_id=user_uuid,
        device_token=token_in.device_token,
        device_name=token_in.device_name,
        platform="ios",
        is_active=True,
    )
    db.add(device_token)
    await db.commit()
    await db.refresh(device_token)

    return DeviceTokenResponse.model_validate(device_token)


@router.delete("/device-token", status_code=status.HTTP_204_NO_CONTENT)
async def unregister_device_token(
    token_in: DeviceTokenDelete,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Unregister a device token (mark as inactive)."""
    user_uuid = UUID(user_id)

    # Find the token
    result = await db.execute(
        select(UserDeviceToken).where(
            and_(
                UserDeviceToken.user_id == user_uuid,
                UserDeviceToken.device_token == token_in.device_token,
            )
        )
    )
    token = result.scalar_one_or_none()

    if token:
        token.is_active = False
        await db.commit()


@router.get("/device-tokens", response_model=list[DeviceTokenResponse])
async def list_device_tokens(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """List all active device tokens for the current user."""
    user_uuid = UUID(user_id)

    result = await db.execute(
        select(UserDeviceToken).where(
            and_(
                UserDeviceToken.user_id == user_uuid,
                UserDeviceToken.is_active == True,
            )
        )
    )
    tokens = result.scalars().all()

    return [DeviceTokenResponse.model_validate(t) for t in tokens]


class TestNotificationRequest(BaseModel):
    title: str = "Test Notification"
    body: str = "This is a test push notification from Orest's Journal!"


class TestNotificationResponse(BaseModel):
    success: bool
    devices_sent: int
    devices_total: int
    message: str


@router.post("/test", response_model=TestNotificationResponse)
async def send_test_notification(
    request: TestNotificationRequest = TestNotificationRequest(),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Send a test push notification to all of the current user's devices."""
    user_uuid = UUID(user_id)

    # Check if APNs is configured
    if not apns_service.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Push notifications not configured. Check APNs settings.",
        )

    # Get all active device tokens for this user
    result = await db.execute(
        select(UserDeviceToken).where(
            and_(
                UserDeviceToken.user_id == user_uuid,
                UserDeviceToken.is_active == True,
            )
        )
    )
    tokens = result.scalars().all()

    if not tokens:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No registered devices found. Make sure you've granted notification permissions.",
        )

    # Send to all devices
    device_tokens = [t.device_token for t in tokens]
    success_count = await apns_service.send_to_multiple(
        device_tokens,
        request.title,
        request.body,
        data={"type": "test"},
    )

    return TestNotificationResponse(
        success=success_count > 0,
        devices_sent=success_count,
        devices_total=len(device_tokens),
        message=f"Sent to {success_count}/{len(device_tokens)} devices",
    )


# Notification Preferences Endpoints

@router.get("/preferences", response_model=NotificationPreferencesResponse)
async def get_notification_preferences(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Get notification preferences for the current user.

    Returns defaults (all True) if no preferences have been set.
    """
    user_uuid = UUID(user_id)

    result = await db.execute(
        select(NotificationPreference).where(
            NotificationPreference.user_id == user_uuid
        )
    )
    prefs = result.scalar_one_or_none()

    if not prefs:
        # Return default preferences (all enabled)
        return NotificationPreferencesResponse(
            family_member_joined=True,
            family_role_changed=True,
            family_member_left=True,
            family_member_left_promoted=True,
            family_account_deleted=True,
            family_account_deleted_promoted=True,
            pet_added=True,
            pet_updated=True,
            pet_deleted=True,
        )

    return NotificationPreferencesResponse.model_validate(prefs)


@router.patch("/preferences", response_model=NotificationPreferencesResponse)
async def update_notification_preferences(
    request: NotificationPreferencesUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Update notification preferences for the current user.

    Creates preferences record if it doesn't exist (upsert pattern).
    Only updates fields that are provided in the request.
    """
    user_uuid = UUID(user_id)

    result = await db.execute(
        select(NotificationPreference).where(
            NotificationPreference.user_id == user_uuid
        )
    )
    prefs = result.scalar_one_or_none()

    if not prefs:
        # Create new preferences with defaults
        prefs = NotificationPreference(user_id=user_uuid)
        db.add(prefs)

    # Update only provided fields
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(prefs, field, value)

    await db.commit()
    await db.refresh(prefs)

    return NotificationPreferencesResponse.model_validate(prefs)
