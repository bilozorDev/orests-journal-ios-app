import uuid
import secrets
import string
from datetime import UTC, datetime

from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship

from app.db.session import Base


# Characters for invite codes - no ambiguous chars (0/O, 1/I/l)
INVITE_CODE_CHARS = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def generate_invite_code(length: int = 8) -> str:
    """Generate a random invite code."""
    return "".join(secrets.choice(INVITE_CODE_CHARS) for _ in range(length))


class User(Base):
    """User authenticated via Sign in with Apple."""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    apple_user_id = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)

    # Brute force protection
    is_locked_out = Column(Boolean, default=False, nullable=False)
    lockout_expires_at = Column(DateTime, nullable=True)
    failed_invite_attempts = Column(Integer, default=0, nullable=False)
    last_failed_invite_at = Column(DateTime, nullable=True)

    # Relationships
    family_memberships = relationship("FamilyMember", back_populates="user", cascade="all, delete-orphan")
    created_families = relationship("Family", back_populates="creator", foreign_keys="Family.created_by")


class Family(Base):
    """Family group for sharing pet data."""
    __tablename__ = "families"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    invite_code = Column(String(8), unique=True, nullable=False, index=True, default=generate_invite_code)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)

    # Relationships
    creator = relationship("User", back_populates="created_families", foreign_keys=[created_by])
    members = relationship("FamilyMember", back_populates="family", cascade="all, delete-orphan")


class FamilyMember(Base):
    """Family membership (many-to-many between users and families)."""
    __tablename__ = "family_members"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    family_id = Column(UUID(as_uuid=True), ForeignKey("families.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(50), default="member", nullable=False)  # 'admin' or 'member'
    joined_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)

    # Relationships
    family = relationship("Family", back_populates="members")
    user = relationship("User", back_populates="family_memberships")

    __table_args__ = (
        # Unique constraint on family_id + user_id
        {"sqlite_autoincrement": True},
    )


class InviteAttemptLog(Base):
    """Log of invite code attempts for brute force protection."""
    __tablename__ = "invite_attempt_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 max length
    attempted_code = Column(String(8), nullable=False)
    attempted_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False, index=True)
    was_successful = Column(Boolean, default=False, nullable=False)


class SecurityAlert(Base):
    """Security alerts for admin review."""
    __tablename__ = "security_alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alert_type = Column(String(50), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    ip_address = Column(String(45), nullable=True)
    description = Column(String(500), nullable=False)
    alert_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False, index=True)
    is_reviewed = Column(Boolean, default=False, nullable=False, index=True)
