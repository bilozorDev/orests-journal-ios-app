import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from app.db.session import Base


class PetHealthCategory(Base):
    __tablename__ = "pet_health_categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("families.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    name_normalized = Column(String(255), nullable=False)  # Lowercase for matching
    embedding = Column(Vector(1536), nullable=True)  # OpenAI embedding dimension
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False)

    # Relationships
    events = relationship("PetHealthEvent", back_populates="category", cascade="all, delete-orphan")


class PetHealthEvent(Base):
    __tablename__ = "pet_health_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pet_id = Column(UUID(as_uuid=True), ForeignKey("pets.id", ondelete="CASCADE"), nullable=False)  # Covered by composite index ix_pet_health_events_pet_occurred
    category_id = Column(UUID(as_uuid=True), ForeignKey("pet_health_categories.id", ondelete="CASCADE"), nullable=False)
    occurred_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False)
    duration_minutes = Column(Integer, nullable=True)  # Optional duration for behavioral events
    notes = Column(Text, nullable=True)
    embedding = Column(Vector(1536), nullable=True)  # OpenAI embedding dimension
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False)

    # Relationships
    pet = relationship("Pet")
    category = relationship("PetHealthCategory", back_populates="events")
    photos = relationship("PetHealthEventPhoto", back_populates="event", cascade="all, delete-orphan", order_by="PetHealthEventPhoto.sort_order")


class PetHealthEventPhoto(Base):
    __tablename__ = "pet_health_event_photos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("pet_health_events.id", ondelete="CASCADE"), nullable=False)
    photo_url = Column(String(512), nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False)

    # Relationships
    event = relationship("PetHealthEvent", back_populates="photos")
