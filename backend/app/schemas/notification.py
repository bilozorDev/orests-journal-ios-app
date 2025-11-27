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
