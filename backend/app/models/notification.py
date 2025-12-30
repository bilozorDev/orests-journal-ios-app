import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base


class UserDeviceToken(Base):
    """Store APNs device tokens for push notifications."""
    __tablename__ = "user_device_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    device_token = Column(String(255), nullable=False)
    device_name = Column(String(255), nullable=True)
    platform = Column(String(20), default="ios", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", backref="device_tokens")

    __table_args__ = (
        # Unique constraint on user_id + device_token
        {"sqlite_autoincrement": True},
    )


class MedicationSchedule(Base):
    """Scheduled times for medication reminders."""
    __tablename__ = "medication_schedules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    medication_id = Column(UUID(as_uuid=True), ForeignKey("pet_medications.id", ondelete="CASCADE"), nullable=False)
    scheduled_hour = Column(Integer, nullable=False)  # 0-23
    scheduled_minute = Column(Integer, default=0, nullable=False)  # 0-59
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    medication = relationship("PetMedication", back_populates="schedules")

    __table_args__ = (
        # Unique constraint on medication_id + hour + minute
        {"sqlite_autoincrement": True},
    )


class NotificationPreference(Base):
    """User notification preferences - controls which notifications they receive."""
    __tablename__ = "notification_preferences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)

    # Family Updates
    family_member_joined = Column(Boolean, default=True, nullable=False)
    family_role_changed = Column(Boolean, default=True, nullable=False)
    family_member_left = Column(Boolean, default=True, nullable=False)
    family_member_left_promoted = Column(Boolean, default=True, nullable=False)
    family_account_deleted = Column(Boolean, default=True, nullable=False)
    family_account_deleted_promoted = Column(Boolean, default=True, nullable=False)

    # Pet Updates
    pet_added = Column(Boolean, default=True, nullable=False)
    pet_updated = Column(Boolean, default=True, nullable=False)
    pet_deleted = Column(Boolean, default=True, nullable=False)

    # Medication Updates
    medication_created = Column(Boolean, default=True, nullable=False)
    medication_updated = Column(Boolean, default=True, nullable=False)
    medication_archived = Column(Boolean, default=True, nullable=False)
    dose_administered = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", backref="notification_preferences")


class NotificationLog(Base):
    """Track sent notifications to prevent duplicates."""
    __tablename__ = "notification_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    medication_id = Column(UUID(as_uuid=True), ForeignKey("pet_medications.id", ondelete="CASCADE"), nullable=False)
    notification_type = Column(String(50), nullable=False)  # 'reminder' or 'missed_dose'
    scheduled_time = Column(DateTime, nullable=False)  # The expected dose time
    sent_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    recipient_count = Column(Integer, default=0, nullable=False)

    # Relationships
    medication = relationship("PetMedication", back_populates="notification_logs")

    __table_args__ = (
        # Unique constraint on medication_id + type + scheduled_time
        {"sqlite_autoincrement": True},
    )
