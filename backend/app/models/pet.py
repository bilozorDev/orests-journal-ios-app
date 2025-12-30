import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Date, ForeignKey, Float, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base


class Pet(Base):
    """Pet belonging to a family."""
    __tablename__ = "pets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    family_id = Column(UUID(as_uuid=True), ForeignKey("families.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    kind = Column(String(100), nullable=False)  # e.g., "cat", "dog"
    photo_url = Column(String(500), nullable=True)
    current_weight = Column(Float, nullable=True)
    date_of_birth = Column(Date, nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    health_records = relationship("HealthRecord", back_populates="pet", cascade="all, delete-orphan")
    feedings = relationship("PetFeeding", back_populates="pet", cascade="all, delete-orphan")
    calorie_goals = relationship("PetCalorieGoal", back_populates="pet", cascade="all, delete-orphan")
    medications = relationship("PetMedication", back_populates="pet", cascade="all, delete-orphan")


class HealthRecord(Base):
    """Health record for weight/age tracking."""
    __tablename__ = "health_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pet_id = Column(UUID(as_uuid=True), ForeignKey("pets.id", ondelete="CASCADE"), nullable=False)
    age_years = Column(Float, nullable=True)
    weight_pounds = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    recorded_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    pet = relationship("Pet", back_populates="health_records")
