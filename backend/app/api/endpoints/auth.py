"""
Authentication endpoints for Sign in with Apple.
Users are stored directly in PostgreSQL.
"""
from typing import Optional, List, Literal
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
import httpx
import jwt as pyjwt
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_db
from app.core.security import create_access_token, get_current_user_id
from app.models.user import User, Family, FamilyMember
from app.models.notification import UserDeviceToken
from app.services.apns import apns_service
from app.cache.helpers import cache_delete
from app.cache.keys import key_family_detail

router = APIRouter()


# --- Pydantic Models ---

class AppleAuthRequest(BaseModel):
    """Request body for Apple Sign-in."""
    identity_token: str  # JWT from Apple
    user_id: str  # Apple's user identifier
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class FamilyResponse(BaseModel):
    """Family data for API responses."""
    id: str
    name: str
    invite_code: str
    role: str  # User's role in this family


class UserResponse(BaseModel):
    """User data for auth responses."""
    id: str
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class AuthResponse(BaseModel):
    """Response from authentication endpoints."""
    token: str
    user: UserResponse
    families: List[FamilyResponse]


class MeResponse(BaseModel):
    """Response for /auth/me endpoint."""
    user: UserResponse
    families: List[FamilyResponse]


class ProfileUpdateRequest(BaseModel):
    """Request body for updating user profile."""
    first_name: str
    last_name: Optional[str] = None


class DeleteAccountRequest(BaseModel):
    """Request body for deleting user account."""
    new_admin_user_id: Optional[str] = None  # Required if only admin with members


class DeleteAccountResponse(BaseModel):
    """Response after deleting account."""
    success: bool
    steps_completed: List[str]


# --- Helper Functions ---

async def verify_apple_identity_token(identity_token: str) -> dict:
    """
    Verify Apple's identity token.
    Apple's public keys are fetched from their JWKS endpoint.
    """
    apple_keys_url = "https://appleid.apple.com/auth/keys"

    async with httpx.AsyncClient() as client:
        response = await client.get(apple_keys_url)
        response.raise_for_status()
        apple_jwks = response.json()

    try:
        # Get the key ID from the token header
        unverified_header = pyjwt.get_unverified_header(identity_token)
        kid = unverified_header.get("kid")

        # Find the matching key
        apple_key = None
        for key in apple_jwks.get("keys", []):
            if key.get("kid") == kid:
                apple_key = key
                break

        if apple_key is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unable to find appropriate Apple key",
            )

        # Construct the public key
        from jwt.algorithms import RSAAlgorithm
        public_key = RSAAlgorithm.from_jwk(apple_key)

        # Verify and decode the token
        payload = pyjwt.decode(
            identity_token,
            public_key,
            algorithms=["RS256"],
            options={"verify_aud": False},  # Skip audience check
        )

        return payload

    except pyjwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Apple token: {str(e)}",
        )


async def get_user_families(db: AsyncSession, user_id: UUID) -> List[FamilyResponse]:
    """Get all families for a user with their role."""
    query = (
        select(FamilyMember)
        .options(selectinload(FamilyMember.family))
        .where(FamilyMember.user_id == user_id)
    )
    result = await db.execute(query)
    memberships = result.scalars().all()

    families = []
    for membership in memberships:
        families.append(FamilyResponse(
            id=str(membership.family.id),
            name=membership.family.name,
            invite_code=membership.family.invite_code,
            role=membership.role,
        ))

    return families


async def get_user_device_tokens(db: AsyncSession, user_id: UUID) -> list[str]:
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


# --- Endpoints ---

@router.post("/apple", response_model=AuthResponse)
async def sign_in_with_apple(
    request: AppleAuthRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate with Apple Sign-in.

    1. Verify Apple's identity token
    2. Find or create user in database
    3. Return our own JWT + user info + families
    """
    # Verify Apple token
    apple_claims = await verify_apple_identity_token(request.identity_token)

    # Get Apple's stable user ID from the token
    apple_user_id = apple_claims.get("sub")
    if not apple_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Apple token missing user ID",
        )

    # Get email from Apple token or request (Apple only provides email on first sign-in)
    email = request.email or apple_claims.get("email")

    # Try to find existing user
    query = select(User).where(User.apple_user_id == apple_user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if user is None:
        # Create new user
        user = User(
            apple_user_id=apple_user_id,
            email=email,
            first_name=request.first_name,
            last_name=request.last_name,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    else:
        # Update user info if provided (Apple only provides name on first sign-in)
        updated = False
        if request.email and not user.email:
            user.email = request.email
            updated = True
        if request.first_name and not user.first_name:
            user.first_name = request.first_name
            updated = True
        if request.last_name and not user.last_name:
            user.last_name = request.last_name
            updated = True
        if updated:
            await db.commit()
            await db.refresh(user)

    # Create our own JWT
    token = create_access_token(str(user.id))

    # Get user's families
    families = await get_user_families(db, user.id)

    return AuthResponse(
        token=token,
        user=UserResponse(
            id=str(user.id),
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
        ),
        families=families,
    )


@router.get("/me", response_model=MeResponse)
async def get_current_user_info(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Get current authenticated user's info and families.
    """
    # Get user from database
    query = select(User).where(User.id == UUID(user_id))
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Get user's families
    families = await get_user_families(db, user.id)

    return MeResponse(
        user=UserResponse(
            id=str(user.id),
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
        ),
        families=families,
    )


@router.patch("/profile", response_model=UserResponse)
async def update_profile(
    request: ProfileUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Update current user's profile (first name, last name).
    Used when Apple doesn't provide name during sign-in.
    """
    # Get user from database
    query = select(User).where(User.id == UUID(user_id))
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Update profile fields
    user.first_name = request.first_name
    if request.last_name is not None:
        user.last_name = request.last_name

    await db.commit()
    await db.refresh(user)

    return UserResponse(
        id=str(user.id),
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
    )


@router.delete("/account", response_model=DeleteAccountResponse)
async def delete_account(
    request: Optional[DeleteAccountRequest] = None,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Delete user account. Handles family scenarios:
    - Only member in family: Delete family + account
    - Other admins exist: Remove from family + notify + delete account
    - Only admin with members: Must specify new_admin_user_id, then delete
    """
    user_uuid = UUID(user_id)
    steps_completed: List[str] = []

    # Get user with memberships
    user_query = select(User).where(User.id == user_uuid)
    result = await db.execute(user_query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user_display_name = get_display_name(user)

    # Get all family memberships
    memberships_query = (
        select(FamilyMember)
        .options(selectinload(FamilyMember.family))
        .where(FamilyMember.user_id == user_uuid)
    )
    result = await db.execute(memberships_query)
    memberships = list(result.scalars().all())

    # Process each family membership
    for membership in memberships:
        family = membership.family
        family_id = family.id
        family_name = family.name
        is_admin = membership.role == "admin"

        # Count other admins and other members
        other_admins_query = select(func.count()).where(
            FamilyMember.family_id == family_id,
            FamilyMember.role == "admin",
            FamilyMember.user_id != user_uuid,
        )
        result = await db.execute(other_admins_query)
        other_admin_count = result.scalar() or 0

        other_members_query = select(func.count()).where(
            FamilyMember.family_id == family_id,
            FamilyMember.user_id != user_uuid,
        )
        result = await db.execute(other_members_query)
        other_member_count = result.scalar() or 0

        if other_member_count == 0:
            # Only member - delete the family entirely
            await db.delete(family)
            steps_completed.append(f"deleted_family_{family_id}")

        elif not is_admin or other_admin_count > 0:
            # Either not admin, or has other admins - just remove from family
            await db.delete(membership)

            # Notify admins about departure
            admin_tokens = await get_admin_device_tokens(db, family_id, exclude_user_id=user_uuid)
            if admin_tokens:
                await apns_service.send_to_multiple(
                    device_tokens=admin_tokens,
                    title=f"{user_display_name} left",
                    body=f"{user_display_name} deleted their account and left {family_name}",
                    data={
                        "type": "account_deleted",
                        "family_id": str(family_id),
                        "user_id": str(user_uuid),
                    },
                )
            steps_completed.append(f"removed_from_family_{family_id}")

        else:
            # Only admin with other members - must promote someone first
            if not request or not request.new_admin_user_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"You are the only admin in {family_name}. Please select a member to become the new admin.",
                )

            new_admin_uuid = UUID(request.new_admin_user_id)

            # Verify new admin is a member
            new_admin_membership_query = (
                select(FamilyMember)
                .options(selectinload(FamilyMember.user))
                .where(
                    FamilyMember.family_id == family_id,
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

            # Promote new admin
            new_admin_membership.role = "admin"
            await db.flush()

            # Remove membership
            await db.delete(membership)

            # Notify new admin
            new_admin_tokens = await get_user_device_tokens(db, new_admin_uuid)
            if new_admin_tokens:
                await apns_service.send_to_multiple(
                    device_tokens=new_admin_tokens,
                    title="You're now an admin",
                    body=f"{user_display_name} made you an admin before deleting their account",
                    data={
                        "type": "account_deleted_promoted",
                        "family_id": str(family_id),
                        "user_id": str(user_uuid),
                    },
                )
            steps_completed.append(f"promoted_admin_and_removed_{family_id}")

        # Invalidate family cache
        await cache_delete(key_family_detail(str(family_id)))

    # Deactivate all device tokens
    tokens_query = select(UserDeviceToken).where(UserDeviceToken.user_id == user_uuid)
    tokens_result = await db.execute(tokens_query)
    tokens = list(tokens_result.scalars().all())
    for token in tokens:
        await db.delete(token)
    steps_completed.append("deleted_device_tokens")

    # Delete the user (cascade handles remaining references)
    await db.delete(user)
    await db.commit()
    steps_completed.append("deleted_account")

    return DeleteAccountResponse(
        success=True,
        steps_completed=steps_completed,
    )


# --- Test Login Endpoint (for UI testing) ---

class DevLoginRequest(BaseModel):
    """Request body for test login (UI testing only)."""
    test_user_id: str = "ui-test-user"
    email: str = "uitest@example.com"
    first_name: str = "UI"
    last_name: str = "Tester"
    create_family: bool = False
    family_name: str = "Test Family"


@router.post("/test-login", response_model=AuthResponse)
async def test_login(
    request: DevLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Test login endpoint for UI automation testing.
    Bypasses Apple Sign-in by creating a test user directly.

    SECURITY: Only available when environment is "development" or "test".
    """
    from app.core.config import get_settings

    settings = get_settings()

    # Security check - only allow in development/test environments
    if settings.environment not in ("development", "test"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Test login is only available in development/test environments",
        )

    # Create unique apple_user_id based on test_user_id
    apple_user_id = f"test_{request.test_user_id}"

    # Find or create test user
    query = select(User).where(User.apple_user_id == apple_user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            apple_user_id=apple_user_id,
            email=request.email,
            first_name=request.first_name,
            last_name=request.last_name,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    # Optionally create family
    if request.create_family:
        # Check if user already has a family
        existing_membership = await db.execute(
            select(FamilyMember).where(FamilyMember.user_id == user.id)
        )
        if existing_membership.scalar_one_or_none() is None:
            family = Family(
                name=request.family_name,
                created_by=user.id,
            )
            db.add(family)
            await db.flush()

            membership = FamilyMember(
                family_id=family.id,
                user_id=user.id,
                role="admin",
            )
            db.add(membership)
            await db.commit()

    # Create JWT token
    token = create_access_token(str(user.id))

    # Get user's families
    families = await get_user_families(db, user.id)

    return AuthResponse(
        token=token,
        user=UserResponse(
            id=str(user.id),
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
        ),
        families=families,
    )


@router.delete("/test-cleanup/{test_user_id}")
async def test_cleanup(
    test_user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Delete test user and all associated data (for UI testing cleanup).

    SECURITY: Only available when environment is "development" or "test".
    """
    from app.core.config import get_settings

    settings = get_settings()

    # Security check - only allow in development/test environments
    if settings.environment not in ("development", "test"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Test cleanup is only available in development/test environments",
        )

    # Build apple_user_id from test_user_id
    apple_user_id = f"test_{test_user_id}"

    # Find the test user
    query = select(User).where(User.apple_user_id == apple_user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if user is None:
        return {"deleted": False, "message": "User not found"}

    # Delete user (cascade will handle family memberships)
    await db.delete(user)
    await db.commit()

    return {"deleted": True, "message": f"Deleted test user {test_user_id}"}
