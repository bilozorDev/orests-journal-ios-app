"""
Family management endpoints with invite code system and brute force protection.
"""
from datetime import datetime, timedelta
from typing import List, Literal, Optional
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends, Request, status
from pydantic import BaseModel
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_db
from app.core.security import get_current_user_id
from app.models.user import User, Family, FamilyMember, InviteAttemptLog, SecurityAlert, generate_invite_code
from app.models.notification import UserDeviceToken
from app.services.apns import apns_service
from app.services.family_notifications import get_filtered_family_member_tokens
from app.cache.helpers import cache_get, cache_set, cache_delete
from app.cache.keys import key_family_detail, TTL_FAMILY

router = APIRouter()

# --- Rate Limiting Constants ---
MAX_ATTEMPTS_PER_USER = 5  # Per hour
MAX_ATTEMPTS_PER_IP = 10  # Per hour
RATE_LIMIT_WINDOW = timedelta(hours=1)

# --- Brute Force Protection Constants ---
BACKOFF_BASE_SECONDS = 60      # 1 min base
BACKOFF_MULTIPLIER = 2
MAX_BACKOFF_SECONDS = 1800     # 30 min max
LOCKOUT_THRESHOLD = 10         # Lock after 10 failures
LOCKOUT_DURATION = timedelta(hours=1)


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


class UpdateRoleRequest(BaseModel):
    """Request to update a member's role."""
    role: Literal["admin", "member"]


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


class LeaveFamilyRequest(BaseModel):
    """Request to leave a family with optional admin promotion."""
    new_admin_user_id: Optional[str] = None  # Required if only admin with members


class LeaveFamilyResponse(BaseModel):
    """Response after leaving a family."""
    success: bool
    action: Literal["left", "left_promoted", "family_deleted"]
    family_name: str


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
    was_successful: bool = False,
) -> None:
    """Log an invite code attempt for rate limiting."""
    log_entry = InviteAttemptLog(
        user_id=user_id,
        ip_address=ip_address,
        attempted_code=attempted_code.upper(),
        was_successful=was_successful,
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


async def get_user_device_tokens(
    db: AsyncSession,
    user_id: UUID,
) -> list[str]:
    """Get active device tokens for a specific user."""
    tokens_query = select(UserDeviceToken.device_token).where(
        and_(
            UserDeviceToken.user_id == user_id,
            UserDeviceToken.is_active == True,
        )
    )
    tokens_result = await db.execute(tokens_query)
    return list(tokens_result.scalars().all())


async def get_admin_device_tokens(
    db: AsyncSession,
    family_id: UUID,
    exclude_user_id: Optional[UUID] = None,
) -> list[str]:
    """Get active device tokens for family admins, optionally excluding a user."""
    # Get user IDs of admins
    admins_query = select(FamilyMember.user_id).where(
        FamilyMember.family_id == family_id,
        FamilyMember.role == "admin",
    )
    if exclude_user_id:
        admins_query = admins_query.where(FamilyMember.user_id != exclude_user_id)

    admins_result = await db.execute(admins_query)
    admin_ids = list(admins_result.scalars().all())

    if not admin_ids:
        return []

    # Get their active device tokens
    tokens_query = select(UserDeviceToken.device_token).where(
        and_(
            UserDeviceToken.user_id.in_(admin_ids),
            UserDeviceToken.is_active == True,
        )
    )
    tokens_result = await db.execute(tokens_query)
    return list(tokens_result.scalars().all())


def get_display_name(user: Optional[User]) -> str:
    """Get display name for a user."""
    if not user:
        return "Someone"
    if user.first_name:
        return user.first_name
    if user.email:
        return user.email.split("@")[0]
    return "Someone"


# --- Brute Force Protection Functions ---

def calculate_backoff_seconds(failed_attempts: int) -> int:
    """
    Calculate exponential backoff wait time.

    Backoff schedule:
    - 1 failure: 60 seconds (1 min)
    - 2 failures: 120 seconds (2 min)
    - 3 failures: 240 seconds (4 min)
    - 4 failures: 480 seconds (8 min)
    - 5 failures: 960 seconds (16 min)
    - 6+ failures: 1800 seconds (30 min max)
    """
    if failed_attempts <= 0:
        return 0

    backoff = BACKOFF_BASE_SECONDS * (BACKOFF_MULTIPLIER ** (failed_attempts - 1))
    return min(backoff, MAX_BACKOFF_SECONDS)


async def check_user_lockout(db: AsyncSession, user_id: UUID) -> None:
    """
    Check if user is locked out. If lockout has expired, clear it.
    Raises HTTPException if user is still locked out.
    """
    user_query = select(User).where(User.id == user_id)
    result = await db.execute(user_query)
    user = result.scalar_one_or_none()

    if not user:
        return

    if user.is_locked_out:
        if user.lockout_expires_at and datetime.utcnow() >= user.lockout_expires_at:
            # Lockout expired - clear it
            user.is_locked_out = False
            user.lockout_expires_at = None
            user.failed_invite_attempts = 0
            user.last_failed_invite_at = None
            await db.commit()
        else:
            # Still locked out
            remaining = user.lockout_expires_at - datetime.utcnow() if user.lockout_expires_at else timedelta(0)
            minutes_remaining = max(1, int(remaining.total_seconds() / 60))
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Account temporarily locked. Try again in {minutes_remaining} minutes.",
            )


async def check_exponential_backoff(db: AsyncSession, user_id: UUID) -> None:
    """
    Check if user must wait due to exponential backoff from failed attempts.
    Raises HTTPException if backoff period hasn't elapsed.
    """
    user_query = select(User).where(User.id == user_id)
    result = await db.execute(user_query)
    user = result.scalar_one_or_none()

    if not user or user.failed_invite_attempts == 0:
        return

    backoff_seconds = calculate_backoff_seconds(user.failed_invite_attempts)

    if user.last_failed_invite_at:
        elapsed = (datetime.utcnow() - user.last_failed_invite_at).total_seconds()
        if elapsed < backoff_seconds:
            wait_remaining = int(backoff_seconds - elapsed)
            if wait_remaining >= 60:
                wait_msg = f"{wait_remaining // 60} minutes"
            else:
                wait_msg = f"{wait_remaining} seconds"
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many failed attempts. Please wait {wait_msg} before trying again.",
            )


async def create_security_alert(
    db: AsyncSession,
    alert_type: str,
    user_id: Optional[UUID],
    ip_address: Optional[str],
    description: str,
    alert_metadata: Optional[dict] = None,
) -> None:
    """Create a security alert for admin review."""
    alert = SecurityAlert(
        alert_type=alert_type,
        user_id=user_id,
        ip_address=ip_address,
        description=description,
        alert_metadata=alert_metadata,
    )
    db.add(alert)


async def handle_failed_invite_attempt(
    db: AsyncSession,
    user_id: UUID,
    ip_address: Optional[str],
    attempted_code: str,
) -> None:
    """
    Handle a failed invite attempt: increment counter, check for lockout trigger.
    """
    user_query = select(User).where(User.id == user_id)
    result = await db.execute(user_query)
    user = result.scalar_one_or_none()

    if not user:
        return

    # Increment failed attempts
    user.failed_invite_attempts = (user.failed_invite_attempts or 0) + 1
    user.last_failed_invite_at = datetime.utcnow()

    # Check if we should trigger lockout
    if user.failed_invite_attempts >= LOCKOUT_THRESHOLD:
        user.is_locked_out = True
        user.lockout_expires_at = datetime.utcnow() + LOCKOUT_DURATION

        # Create security alert
        await create_security_alert(
            db=db,
            alert_type="account_lockout",
            user_id=user_id,
            ip_address=ip_address,
            description=f"Account locked after {user.failed_invite_attempts} failed invite code attempts",
            alert_metadata={
                "attempted_code": attempted_code,
                "lockout_expires_at": user.lockout_expires_at.isoformat(),
            }
        )

    await db.commit()


async def handle_successful_invite_attempt(db: AsyncSession, user_id: UUID) -> None:
    """
    Reset failed attempt counters on successful invite code use.
    """
    user_query = select(User).where(User.id == user_id)
    result = await db.execute(user_query)
    user = result.scalar_one_or_none()

    if user and user.failed_invite_attempts > 0:
        user.failed_invite_attempts = 0
        user.last_failed_invite_at = None
        await db.commit()


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
    Protected against brute force attacks with rate limiting, exponential backoff,
    and account lockout.
    """
    user_uuid = UUID(user_id)
    ip_address = get_client_ip(http_request)
    invite_code = request.invite_code.upper().strip()

    # Check if account is locked out
    await check_user_lockout(db, user_uuid)

    # Check exponential backoff (must wait between attempts)
    await check_exponential_backoff(db, user_uuid)

    # Check rate limits before processing
    await check_rate_limit(db, user_uuid, ip_address)

    # Find family by invite code
    family_query = select(Family).where(Family.invite_code == invite_code)
    result = await db.execute(family_query)
    family = result.scalar_one_or_none()

    if not family:
        # Log failed attempt and handle backoff/lockout
        await log_invite_attempt(db, user_uuid, ip_address, invite_code, was_successful=False)
        await handle_failed_invite_attempt(db, user_uuid, ip_address, invite_code)
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

    # Log successful attempt and reset failure counters
    await log_invite_attempt(db, user_uuid, ip_address, invite_code, was_successful=True)
    await handle_successful_invite_attempt(db, user_uuid)

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

    tokens = await get_filtered_family_member_tokens(db, family.id, user_uuid, "member_joined")
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
    try:
        family_uuid = UUID(family_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid family_id format",
        )
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

    # Get family name for notification before deleting
    family_query = select(Family).where(Family.id == family_uuid)
    family_result = await db.execute(family_query)
    family = family_result.scalar_one_or_none()
    family_name = family.name if family else "the family"

    await db.delete(target_membership)
    await db.commit()

    # Invalidate family cache since member list changed
    await cache_delete(key_family_detail(family_id))

    # Send notification to the removed user (not for self-removal)
    if not is_self:
        tokens = await get_user_device_tokens(db, target_uuid)
        if tokens:
            await apns_service.send_to_multiple(
                device_tokens=tokens,
                title="You were removed",
                body=f"You are no longer a member of {family_name}",
                data={
                    "type": "member_removed",
                    "family_id": str(family_uuid),
                    "family_name": family_name,
                },
            )

    return {"message": "Member removed successfully"}


@router.patch("/{family_id}/members/{member_user_id}/role", response_model=FamilyMemberResponse)
async def update_member_role(
    family_id: str,
    member_user_id: str,
    request: UpdateRoleRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Update a family member's role. Only admins can change roles.
    Sends a notification to the affected member.
    """
    family_uuid = UUID(family_id)
    user_uuid = UUID(user_id)
    target_uuid = UUID(member_user_id)
    new_role = request.role  # Validated by Pydantic Literal type

    # Check if current user is an admin of this family
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

    if current_membership.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only family admins can change member roles",
        )

    # Get target membership with user info
    target_membership_query = (
        select(FamilyMember)
        .options(selectinload(FamilyMember.user))
        .where(
            FamilyMember.family_id == family_uuid,
            FamilyMember.user_id == target_uuid,
        )
    )
    result = await db.execute(target_membership_query)
    target_membership = result.scalar_one_or_none()

    if not target_membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found in this family",
        )

    # Prevent demoting the last admin
    if target_membership.role == "admin" and new_role == "member":
        admin_count_query = select(func.count()).where(
            FamilyMember.family_id == family_uuid,
            FamilyMember.role == "admin",
        )
        result = await db.execute(admin_count_query)
        admin_count = result.scalar() or 0

        if admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot demote the last admin. Promote another member first.",
            )

    # Update the role
    old_role = target_membership.role
    target_membership.role = new_role
    await db.commit()
    await db.refresh(target_membership)

    # Invalidate family cache
    await cache_delete(key_family_detail(family_id))

    # Send notification to the affected member (if role actually changed)
    if old_role != new_role:
        # Get family name for notification
        family_query = select(Family).where(Family.id == family_uuid)
        family_result = await db.execute(family_query)
        family = family_result.scalar_one_or_none()
        family_name = family.name if family else "your family"

        role_display = "an admin" if new_role == "admin" else "a member"
        tokens = await get_user_device_tokens(db, target_uuid)
        if tokens:
            await apns_service.send_to_multiple(
                device_tokens=tokens,
                title="Your role was updated",
                body=f"You are now {role_display} in {family_name}",
                data={
                    "type": "role_changed",
                    "family_id": str(family_uuid),
                    "new_role": new_role,
                },
            )

    return FamilyMemberResponse(
        id=str(target_membership.id),
        user_id=str(target_membership.user_id),
        email=target_membership.user.email if target_membership.user else None,
        first_name=target_membership.user.first_name if target_membership.user else None,
        last_name=target_membership.user.last_name if target_membership.user else None,
        role=target_membership.role,
        joined_at=target_membership.joined_at,
    )


@router.post("/{family_id}/leave", response_model=LeaveFamilyResponse)
async def leave_family(
    family_id: str,
    request: Optional[LeaveFamilyRequest] = None,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Leave a family. Handles different scenarios:
    - Member (admins exist): Leave, notify admins
    - Admin (other admins exist): Leave, notify other admins
    - Admin (no other admins, no other members): Delete family
    - Admin (no other admins, has other members): Must specify new_admin_user_id
    """
    family_uuid = UUID(family_id)
    user_uuid = UUID(user_id)

    # Get current user's membership with user info
    current_membership_query = (
        select(FamilyMember)
        .options(selectinload(FamilyMember.user))
        .where(
            FamilyMember.family_id == family_uuid,
            FamilyMember.user_id == user_uuid,
        )
    )
    result = await db.execute(current_membership_query)
    current_membership = result.scalar_one_or_none()

    if not current_membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this family",
        )

    # Get family info
    family_query = select(Family).where(Family.id == family_uuid)
    family_result = await db.execute(family_query)
    family = family_result.scalar_one_or_none()

    if not family:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Family not found",
        )

    family_name = family.name
    is_admin = current_membership.role == "admin"
    user_display_name = get_display_name(current_membership.user)

    # Count other admins and other members
    other_admins_query = select(func.count()).where(
        FamilyMember.family_id == family_uuid,
        FamilyMember.role == "admin",
        FamilyMember.user_id != user_uuid,
    )
    result = await db.execute(other_admins_query)
    other_admin_count = result.scalar() or 0

    other_members_query = select(func.count()).where(
        FamilyMember.family_id == family_uuid,
        FamilyMember.user_id != user_uuid,
    )
    result = await db.execute(other_members_query)
    other_member_count = result.scalar() or 0

    action: Literal["left", "left_promoted", "family_deleted"]

    if not is_admin:
        # Member leaving - just remove and notify admins
        await db.delete(current_membership)
        await db.commit()
        action = "left"

        # Notify admins
        admin_tokens = await get_admin_device_tokens(db, family_uuid)
        if admin_tokens:
            await apns_service.send_to_multiple(
                device_tokens=admin_tokens,
                title=f"{user_display_name} left",
                body=f"{user_display_name} left {family_name}",
                data={
                    "type": "member_left",
                    "family_id": str(family_uuid),
                    "user_id": str(user_uuid),
                },
            )

    elif other_admin_count > 0:
        # Admin leaving but other admins exist - just remove and notify other admins
        await db.delete(current_membership)
        await db.commit()
        action = "left"

        # Notify other admins
        admin_tokens = await get_admin_device_tokens(db, family_uuid, exclude_user_id=user_uuid)
        if admin_tokens:
            await apns_service.send_to_multiple(
                device_tokens=admin_tokens,
                title=f"{user_display_name} left",
                body=f"{user_display_name} left {family_name}",
                data={
                    "type": "member_left",
                    "family_id": str(family_uuid),
                    "user_id": str(user_uuid),
                },
            )

    elif other_member_count == 0:
        # Only admin, no other members - delete the family entirely
        await db.delete(family)
        await db.commit()
        action = "family_deleted"

    else:
        # Only admin with other members - must promote someone first
        if not request or not request.new_admin_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You are the only admin. Please select a member to become the new admin.",
            )

        new_admin_uuid = UUID(request.new_admin_user_id)

        # Verify the new admin is a member of this family
        new_admin_membership_query = (
            select(FamilyMember)
            .options(selectinload(FamilyMember.user))
            .where(
                FamilyMember.family_id == family_uuid,
                FamilyMember.user_id == new_admin_uuid,
            )
        )
        result = await db.execute(new_admin_membership_query)
        new_admin_membership = result.scalar_one_or_none()

        if not new_admin_membership:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Selected user is not a member of this family",
            )

        if new_admin_uuid == user_uuid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot select yourself as the new admin",
            )

        # Promote the new admin
        new_admin_membership.role = "admin"
        await db.flush()

        # Remove current user's membership
        await db.delete(current_membership)
        await db.commit()
        action = "left_promoted"

        # Notify the new admin with consolidated message
        new_admin_tokens = await get_user_device_tokens(db, new_admin_uuid)
        if new_admin_tokens:
            await apns_service.send_to_multiple(
                device_tokens=new_admin_tokens,
                title="You're now an admin",
                body=f"{user_display_name} made you an admin before leaving {family_name}",
                data={
                    "type": "member_left_promoted",
                    "family_id": str(family_uuid),
                    "user_id": str(user_uuid),
                },
            )

    # Invalidate family cache
    await cache_delete(key_family_detail(family_id))

    return LeaveFamilyResponse(
        success=True,
        action=action,
        family_name=family_name,
    )
