import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Float, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from app.db.session import Base


class FoodCategory(str, enum.Enum):
    DRY = "dry"
    WET = "wet"
    SNACK = "snack"


class ContainerUnit(str, enum.Enum):
    GRAMS = "g"
    OUNCES = "oz"
    KILOGRAMS = "kg"
    POUNDS = "lb"


class PetFood(Base):
    """Food item available for a family."""
    __tablename__ = "pet_foods"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("families.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    category = Column(String(50), nullable=False)
    calories_per_kg = Column(Float, nullable=False)
    container_size = Column(Float, nullable=False)
    container_size_unit = Column(String(10), nullable=False, server_default='g')
    image_url = Column(String(500), nullable=True)
    is_archived = Column(Boolean, nullable=False, server_default='false', default=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    feedings = relationship("PetFeeding", back_populates="food", cascade="all, delete-orphan")


class PetFeeding(Base):
    """Record of a pet being fed."""
    __tablename__ = "pet_feedings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pet_id = Column(UUID(as_uuid=True), ForeignKey("pets.id", ondelete="CASCADE"), nullable=False)
    food_id = Column(UUID(as_uuid=True), ForeignKey("pet_foods.id", ondelete="CASCADE"), nullable=False)
    fed_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    fed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    amount = Column(Float, nullable=False)
    amount_unit = Column(String(10), nullable=False, server_default='g')
    calories = Column(Float, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    pet = relationship("Pet", back_populates="feedings")
    food = relationship("PetFood", back_populates="feedings")


class PetCalorieGoal(Base):
    """Daily calorie goal for a pet."""
    __tablename__ = "pet_calorie_goals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pet_id = Column(UUID(as_uuid=True), ForeignKey("pets.id", ondelete="CASCADE"), nullable=False)
    daily_calories = Column(Float, nullable=False)
    effective_from = Column(DateTime, default=datetime.utcnow, nullable=False)
    effective_until = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    pet = relationship("Pet", back_populates="calorie_goals")
