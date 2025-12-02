"""
Authentication endpoints for Sign in with Apple.
Users are stored directly in PostgreSQL.
"""
from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
import httpx
import jwt as pyjwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_db
from app.core.security import create_access_token, get_current_user_id
from app.models.user import User, Family, FamilyMember

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
