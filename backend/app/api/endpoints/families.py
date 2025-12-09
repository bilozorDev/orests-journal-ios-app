"""
Family management endpoints with invite code system and brute force protection.
"""
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends, Request, status
from pydantic import BaseModel
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_db
from app.core.security import get_current_user_id
from app.models.user import User, Family, FamilyMember, InviteAttemptLog, generate_invite_code
from app.models.notification import UserDeviceToken
from app.services.apns import apns_service
from app.cache.helpers import cache_get, cache_set, cache_delete
from app.cache.keys import key_family_detail, TTL_FAMILY

router = APIRouter()

# --- Rate Limiting Constants ---
MAX_ATTEMPTS_PER_USER = 5  # Per hour
MAX_ATTEMPTS_PER_IP = 10  # Per hour
RATE_LIMIT_WINDOW = timedelta(hours=1)


# --- Pydantic Models ---

class CreateFamilyRequest(BaseModel):
    """Request to create a new family."""
    name: str


class JoinFamilyRequest(BaseModel):
    """Request to join a family with invite code."""
    invite_code: str


class UpdateFamilyRequest(BaseModel):
    """Request to update family details."""
    name: str


class FamilyMemberResponse(BaseModel):
    """Family member data for responses."""
    id: str
    user_id: str
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: str
    joined_at: datetime


class FamilyDetailResponse(BaseModel):
    """Detailed family data including members."""
    id: str
    name: str
    invite_code: str
    created_at: datetime
    members: List[FamilyMemberResponse]


class FamilyResponse(BaseModel):
    """Basic family data for responses."""
    id: str
    name: str
    invite_code: str
    role: str  # User's role in this family


class JoinFamilyResponse(BaseModel):
    """Response after successfully joining a family."""
    family: FamilyResponse
    message: str


# --- Helper Functions ---

async def check_rate_limit(
    db: AsyncSession,
    user_id: Optional[UUID],
    ip_address: Optional[str],
) -> None:
    """
    Check if the user or IP has exceeded rate limits for invite attempts.
    Raises HTTPException if rate limited.
    """
    window_start = datetime.utcnow() - RATE_LIMIT_WINDOW

    # Check user-based rate limit
    if user_id:
        user_query = select(func.count()).where(
            InviteAttemptLog.user_id == user_id,
            InviteAttemptLog.attempted_at >= window_start,
        )
        result = await db.execute(user_query)
        user_attempts = result.scalar() or 0

        if user_attempts >= MAX_ATTEMPTS_PER_USER:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many invite code attempts. Please try again later.",
            )

    # Check IP-based rate limit
    if ip_address:
        ip_query = select(func.count()).where(
            InviteAttemptLog.ip_address == ip_address,
            InviteAttemptLog.attempted_at >= window_start,
        )
        result = await db.execute(ip_query)
        ip_attempts = result.scalar() or 0

        if ip_attempts >= MAX_ATTEMPTS_PER_IP:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many invite code attempts from this location. Please try again later.",
            )


async def log_invite_attempt(
    db: AsyncSession,
    user_id: Optional[UUID],
    ip_address: Optional[str],
    attempted_code: str,
) -> None:
    """Log an invite code attempt for rate limiting."""
    log_entry = InviteAttemptLog(
        user_id=user_id,
        ip_address=ip_address,
        attempted_code=attempted_code.upper(),
    )
    db.add(log_entry)
    await db.commit()


def get_client_ip(request: Request) -> Optional[str]:
    """Extract client IP address from request."""
    # Check for forwarded headers (if behind proxy)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


async def get_other_family_member_tokens(
    db: AsyncSession,
    family_id: UUID,
    exclude_user_id: UUID,
) -> list[str]:
    """Get active device tokens for family members except the specified user."""
    # Get user IDs of other family members
    members_query = select(FamilyMember.user_id).where(
        and_(
            FamilyMember.family_id == family_id,
            FamilyMember.user_id != exclude_user_id,
        )
    )
    members_result = await db.execute(members_query)
    user_ids = list(members_result.scalars().all())

    if not user_ids:
        return []

    # Get their active device tokens
    tokens_query = select(UserDeviceToken.device_token).where(
        and_(
            UserDeviceToken.user_id.in_(user_ids),
            UserDeviceToken.is_active == True,
        )
    )
    tokens_result = await db.execute(tokens_query)
    return list(tokens_result.scalars().all())


# --- Endpoints ---

@router.post("", response_model=FamilyResponse)
async def create_family(
    request: CreateFamilyRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Create a new family. The creating user becomes the admin.
    """
    user_uuid = UUID(user_id)

    # Create the family
    family = Family(
        name=request.name,
        created_by=user_uuid,
    )
    db.add(family)
    await db.flush()  # Get the family ID

    # Add the creator as admin
    membership = FamilyMember(
        family_id=family.id,
        user_id=user_uuid,
        role="admin",
    )
    db.add(membership)
    await db.commit()
    await db.refresh(family)

    return FamilyResponse(
        id=str(family.id),
        name=family.name,
        invite_code=family.invite_code,
        role="admin",
    )


@router.get("/{family_id}", response_model=FamilyDetailResponse)
async def get_family(
    family_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Get family details including members. User must be a member.
    """
    family_uuid = UUID(family_id)
    user_uuid = UUID(user_id)

    # Check if user is a member
    membership_query = select(FamilyMember).where(
        FamilyMember.family_id == family_uuid,
        FamilyMember.user_id == user_uuid,
    )
    result = await db.execute(membership_query)
    membership = result.scalar_one_or_none()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this family",
        )

    # Try cache first
    cache_key = key_family_detail(family_id)
    cached = await cache_get(cache_key, FamilyDetailResponse)
    if cached:
        return cached

    # Get family with members from database
    family_query = (
        select(Family)
        .options(selectinload(Family.members).selectinload(FamilyMember.user))
        .where(Family.id == family_uuid)
    )
    result = await db.execute(family_query)
    family = result.scalar_one_or_none()

    if not family:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Family not found",
        )

    members = [
        FamilyMemberResponse(
            id=str(member.id),
            user_id=str(member.user_id),
            email=member.user.email if member.user else None,
            first_name=member.user.first_name if member.user else None,
            last_name=member.user.last_name if member.user else None,
            role=member.role,
            joined_at=member.joined_at,
        )
        for member in family.members
    ]

    response = FamilyDetailResponse(
        id=str(family.id),
        name=family.name,
        invite_code=family.invite_code,
        created_at=family.created_at,
        members=members,
    )

    # Cache the response
    await cache_set(cache_key, response, TTL_FAMILY)

    return response


@router.post("/join", response_model=JoinFamilyResponse)
async def join_family(
    request: JoinFamilyRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Join a family using an invite code.
    Protected against brute force attacks with rate limiting.
    """
    user_uuid = UUID(user_id)
    ip_address = get_client_ip(http_request)
    invite_code = request.invite_code.upper().strip()

    # Check rate limits before processing
    await check_rate_limit(db, user_uuid, ip_address)

    # Log this attempt (before checking if code is valid)
    await log_invite_attempt(db, user_uuid, ip_address, invite_code)

    # Find family by invite code
    family_query = select(Family).where(Family.invite_code == invite_code)
    result = await db.execute(family_query)
    family = result.scalar_one_or_none()

    if not family:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid invite code",
        )

    # Check if already a member
    existing_query = select(FamilyMember).where(
        FamilyMember.family_id == family.id,
        FamilyMember.user_id == user_uuid,
    )
    result = await db.execute(existing_query)
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already a member of this family",
        )

    # Add user as member
    membership = FamilyMember(
        family_id=family.id,
        user_id=user_uuid,
        role="member",
    )
    db.add(membership)
    await db.commit()

    # Invalidate family cache since member list changed
    await cache_delete(key_family_detail(str(family.id)))

    # Send notification to other family members
    user_query = select(User).where(User.id == user_uuid)
    user_result = await db.execute(user_query)
    new_user = user_result.scalar_one_or_none()

    # Build member name for notification
    member_name = "Someone"
    if new_user:
        if new_user.first_name:
            member_name = new_user.first_name
        elif new_user.email:
            member_name = new_user.email.split("@")[0]

    tokens = await get_other_family_member_tokens(db, family.id, user_uuid)
    if tokens:
        await apns_service.send_to_multiple(
            device_tokens=tokens,
            title=f"{member_name} joined {family.name}",
            body="A new member has joined your family",
            data={
                "type": "member_joined",
                "family_id": str(family.id),
                "user_id": str(user_uuid),
            },
        )

    return JoinFamilyResponse(
        family=FamilyResponse(
            id=str(family.id),
            name=family.name,
            invite_code=family.invite_code,
            role="member",
        ),
        message=f"Successfully joined {family.name}!",
    )


@router.post("/{family_id}/regenerate-code", response_model=FamilyResponse)
async def regenerate_invite_code(
    family_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Generate a new invite code for the family. Only admins can do this.
    """
    family_uuid = UUID(family_id)
    user_uuid = UUID(user_id)

    # Check if user is an admin of this family
    membership_query = select(FamilyMember).where(
        FamilyMember.family_id == family_uuid,
        FamilyMember.user_id == user_uuid,
    )
    result = await db.execute(membership_query)
    membership = result.scalar_one_or_none()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this family",
        )

    if membership.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only family admins can regenerate invite codes",
        )

    # Get and update the family
    family_query = select(Family).where(Family.id == family_uuid)
    result = await db.execute(family_query)
    family = result.scalar_one_or_none()

    if not family:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Family not found",
        )

    # Generate new invite code
    family.invite_code = generate_invite_code()
    await db.commit()
    await db.refresh(family)

    # Invalidate family cache
    await cache_delete(key_family_detail(family_id))

    return FamilyResponse(
        id=str(family.id),
        name=family.name,
        invite_code=family.invite_code,
        role="admin",
    )


@router.patch("/{family_id}", response_model=FamilyResponse)
async def update_family(
    family_id: str,
    request: UpdateFamilyRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Update family details. Only admins can update the family.
    """
    family_uuid = UUID(family_id)
    user_uuid = UUID(user_id)

    # Check if user is an admin of this family
    membership_query = select(FamilyMember).where(
        FamilyMember.family_id == family_uuid,
        FamilyMember.user_id == user_uuid,
    )
    result = await db.execute(membership_query)
    membership = result.scalar_one_or_none()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this family",
        )

    if membership.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only family admins can update family details",
        )

    # Get and update the family
    family_query = select(Family).where(Family.id == family_uuid)
    result = await db.execute(family_query)
    family = result.scalar_one_or_none()

    if not family:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Family not found",
        )

    # Update the family name
    family.name = request.name
    await db.commit()
    await db.refresh(family)

    # Invalidate family cache
    await cache_delete(key_family_detail(family_id))

    return FamilyResponse(
        id=str(family.id),
        name=family.name,
        invite_code=family.invite_code,
        role="admin",
    )


@router.delete("/{family_id}/members/{member_user_id}")
async def remove_family_member(
    family_id: str,
    member_user_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Remove a member from the family. Admins can remove anyone, members can only leave.
    """
    family_uuid = UUID(family_id)
    user_uuid = UUID(user_id)
    target_uuid = UUID(member_user_id)

    # Get current user's membership
    current_membership_query = select(FamilyMember).where(
        FamilyMember.family_id == family_uuid,
        FamilyMember.user_id == user_uuid,
    )
    result = await db.execute(current_membership_query)
    current_membership = result.scalar_one_or_none()

    if not current_membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this family",
        )

    # Check permissions
    is_admin = current_membership.role == "admin"
    is_self = user_uuid == target_uuid

    if not is_admin and not is_self:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only remove yourself or be an admin to remove others",
        )

    # Get target membership
    target_membership_query = select(FamilyMember).where(
        FamilyMember.family_id == family_uuid,
        FamilyMember.user_id == target_uuid,
    )
    result = await db.execute(target_membership_query)
    target_membership = result.scalar_one_or_none()

    if not target_membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found in this family",
        )

    # Prevent removing the last admin
    if target_membership.role == "admin":
        admin_count_query = select(func.count()).where(
            FamilyMember.family_id == family_uuid,
            FamilyMember.role == "admin",
        )
        result = await db.execute(admin_count_query)
        admin_count = result.scalar() or 0

        if admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove the last admin. Transfer admin role first.",
            )

    await db.delete(target_membership)
    await db.commit()

    # Invalidate family cache since member list changed
    await cache_delete(key_family_detail(family_id))

    return {"message": "Member removed successfully"}
