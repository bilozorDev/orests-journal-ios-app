import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Text
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
    name = Column(String(255), nullable=False)
    medication_type = Column(String(50), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=True)
    times_per_day = Column(Integer, default=1, nullable=False)
    notes = Column(Text, nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    pet = relationship("Pet", back_populates="medications")
    doses = relationship("PetMedicationDose", back_populates="medication", cascade="all, delete-orphan")


class PetMedicationDose(Base):
    __tablename__ = "pet_medication_doses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    medication_id = Column(UUID(as_uuid=True), ForeignKey("pet_medications.id", ondelete="CASCADE"), nullable=False)
    given_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    given_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    medication = relationship("PetMedication", back_populates="doses")
