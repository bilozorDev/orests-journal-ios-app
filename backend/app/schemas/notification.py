from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict


# Device Token Schemas
class DeviceTokenCreate(BaseModel):
    device_token: str
    device_name: Optional[str] = None


class DeviceTokenDelete(BaseModel):
    device_token: str


class DeviceTokenResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    device_token: str
    device_name: Optional[str] = None
    platform: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


# Schedule Schemas (for API endpoints)
class ScheduleSetRequest(BaseModel):
    """Request body for setting medication schedules."""
    scheduled_times: list[dict]  # [{"hour": 8, "minute": 0}, {"hour": 20, "minute": 0}]


class ScheduleResponse(BaseModel):
    """Response for medication schedule."""
    medication_id: UUID
    scheduled_times: list[dict]  # [{"hour": 8, "minute": 0}, ...]


# Notification Log Schemas
class NotificationLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    medication_id: UUID
    notification_type: str
    scheduled_time: datetime
    sent_at: datetime
    recipient_count: int


# Notification Preferences Schemas
class NotificationPreferencesUpdate(BaseModel):
    """Request to update notification preferences. All fields optional - only update provided ones."""
    # Family Updates
    family_member_joined: Optional[bool] = None
    family_role_changed: Optional[bool] = None
    family_member_left: Optional[bool] = None
    family_member_left_promoted: Optional[bool] = None
    family_account_deleted: Optional[bool] = None
    family_account_deleted_promoted: Optional[bool] = None

    # Pet Updates
    pet_added: Optional[bool] = None
    pet_updated: Optional[bool] = None
    pet_deleted: Optional[bool] = None

    # Medication Updates
    medication_created: Optional[bool] = None
    medication_updated: Optional[bool] = None
    medication_archived: Optional[bool] = None


class NotificationPreferencesResponse(BaseModel):
    """Response with all notification preferences."""
    model_config = ConfigDict(from_attributes=True)

    # Family Updates
    family_member_joined: bool
    family_role_changed: bool
    family_member_left: bool
    family_member_left_promoted: bool
    family_account_deleted: bool
    family_account_deleted_promoted: bool

    # Pet Updates
    pet_added: bool
    pet_updated: bool
    pet_deleted: bool

    # Medication Updates
    medication_created: bool
    medication_updated: bool
    medication_archived: bool
