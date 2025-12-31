import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from app.db.session import Base


class MedicationType(str, enum.Enum):
    DROPS = "drops"
    PILL = "pill"
    INHALER = "inhaler"
    SHOT = "shot"
    LIQUID = "liquid"
    TABLET = "tablet"
    CAPSULE = "capsule"
    TOPICAL = "topical"


class PetMedication(Base):
    __tablename__ = "pet_medications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pet_id = Column(UUID(as_uuid=True), ForeignKey("pets.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)  # Full medical name
    friendly_name = Column(String(100), nullable=True)  # Short name for notifications/widget
    medication_type = Column(String(50), nullable=False)
    dosage = Column(String(255), nullable=True)
    interval_days = Column(Integer, nullable=True)  # 1-30 for scheduled, null for PRN
    is_as_needed = Column(Boolean, default=False, nullable=False)  # PRN medication
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=True)
    times_per_day = Column(Integer, default=1, nullable=False)
    notes = Column(Text, nullable=True)
    reminders_enabled = Column(Boolean, default=False, nullable=False)
    timezone = Column(String(50), default="UTC", nullable=False)
    is_archived = Column(Boolean, default=False, nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), nullable=False)

    # Relationships
    pet = relationship("Pet", back_populates="medications")
    doses = relationship("PetMedicationDose", back_populates="medication", cascade="all, delete-orphan")
    schedules = relationship("MedicationSchedule", back_populates="medication", cascade="all, delete-orphan")
    notification_logs = relationship("NotificationLog", back_populates="medication", cascade="all, delete-orphan")
    photos = relationship("PetMedicationPhoto", back_populates="medication", cascade="all, delete-orphan", order_by="PetMedicationPhoto.sort_order")


class PetMedicationPhoto(Base):
    __tablename__ = "pet_medication_photos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    medication_id = Column(UUID(as_uuid=True), ForeignKey("pet_medications.id", ondelete="CASCADE"), nullable=False)
    photo_url = Column(String(512), nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), nullable=False)

    # Relationships
    medication = relationship("PetMedication", back_populates="photos")


class PetMedicationDose(Base):
    __tablename__ = "pet_medication_doses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    medication_id = Column(UUID(as_uuid=True), ForeignKey("pet_medications.id", ondelete="CASCADE"), nullable=False)
    given_at = Column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), nullable=False)
    given_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), nullable=False)

    # Relationships
    medication = relationship("PetMedication", back_populates="doses")
