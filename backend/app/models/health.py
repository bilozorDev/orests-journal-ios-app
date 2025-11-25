import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from app.db.session import Base


class PetHealthCategory(Base):
    __tablename__ = "pet_health_categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pet_id = Column(UUID(as_uuid=True), ForeignKey("pets.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    name_normalized = Column(String(255), nullable=False)  # Lowercase for matching
    embedding = Column(Vector(1536), nullable=True)  # OpenAI embedding dimension
    created_by = Column(String(255), nullable=False)  # Clerk user ID
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    pet = relationship("Pet", back_populates="health_categories")
    events = relationship("PetHealthEvent", back_populates="category", cascade="all, delete-orphan")


class PetHealthEvent(Base):
    __tablename__ = "pet_health_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category_id = Column(UUID(as_uuid=True), ForeignKey("pet_health_categories.id", ondelete="CASCADE"), nullable=False)
    occurred_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    notes = Column(Text, nullable=True)
    embedding = Column(Vector(1536), nullable=True)  # OpenAI embedding dimension
    created_by = Column(String(255), nullable=False)  # Clerk user ID
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    category = relationship("PetHealthCategory", back_populates="events")
