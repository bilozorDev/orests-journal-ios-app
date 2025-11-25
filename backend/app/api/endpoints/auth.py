"""
Authentication endpoints for Sign in with Apple + Clerk backend.
"""
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
import httpx
import jwt as pyjwt
from clerk_backend_api import Clerk
from clerk_backend_api.models import ClerkErrors

from app.core.config import get_settings
from app.core.security import get_current_user, ClerkUser

router = APIRouter()


# --- Pydantic Models ---

class AppleAuthRequest(BaseModel):
    """Request body for Apple Sign-in."""
    identity_token: str  # JWT from Apple
    user_id: str  # Apple's user identifier
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class OrganizationResponse(BaseModel):
    """Organization data."""
    id: str
    name: str
    slug: Optional[str] = None


class UserResponse(BaseModel):
    """User data for auth responses."""
    id: str
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class AuthResponse(BaseModel):
    """Response from authentication endpoints."""
    token: str  # Clerk session JWT
    user: UserResponse
    organizations: List[OrganizationResponse]


class MeResponse(BaseModel):
    """Response for /auth/me endpoint."""
    user: UserResponse
    organizations: List[OrganizationResponse]


class CreateOrganizationRequest(BaseModel):
    """Request to create a new organization."""
    name: str


# --- Helper Functions ---

async def verify_apple_identity_token(identity_token: str) -> dict:
    """
    Verify Apple's identity token.

    Apple's public keys are fetched from their JWKS endpoint.
    The token is verified against Apple's public keys.
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
            audience=get_settings().clerk_publishable_key.split("_")[0],  # Your app's bundle ID typically
            options={"verify_aud": False},  # Skip audience check for now
        )

        return payload

    except pyjwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Apple token: {str(e)}",
        )


def get_clerk_client() -> Clerk:
    """Get configured Clerk client."""
    settings = get_settings()
    return Clerk(bearer_auth=settings.clerk_secret_key)


async def get_user_organizations(clerk: Clerk, user_id: str) -> List[OrganizationResponse]:
    """Get all organizations for a user."""
    organizations = []

    try:
        # Get user's organization memberships
        memberships = clerk.users.get_organization_memberships(user_id=user_id)

        if memberships and hasattr(memberships, 'data'):
            for membership in memberships.data:
                if membership.organization:
                    org = membership.organization
                    organizations.append(OrganizationResponse(
                        id=org.id,
                        name=org.name,
                        slug=org.slug if hasattr(org, 'slug') else None,
                    ))
    except Exception as e:
        print(f"Error fetching organizations: {e}")

    return organizations


# --- Endpoints ---

@router.post("/apple", response_model=AuthResponse)
async def sign_in_with_apple(request: AppleAuthRequest):
    """
    Authenticate with Apple Sign-in.

    1. Verify Apple's identity token
    2. Find or create user in Clerk
    3. Create a Clerk session
    4. Return session token + user info + organizations
    """
    # Verify Apple token
    apple_claims = await verify_apple_identity_token(request.identity_token)

    # Get email from Apple token or request
    email = request.email or apple_claims.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is required for sign-in",
        )

    settings = get_settings()

    with get_clerk_client() as clerk:
        # Try to find existing user by email
        existing_users = clerk.users.list(request={"email_address": [email]})

        user = None
        if existing_users and len(existing_users) > 0:
            # User exists
            user = existing_users[0]
        else:
            # Create new user
            # Apple only provides name on first sign-in, use defaults if missing
            try:
                user = clerk.users.create(
                    email_address=[email],
                    first_name=request.first_name or "User",
                    last_name=request.last_name or "",
                    external_id=f"apple_{request.user_id}",  # Link Apple ID
                    skip_password_requirement=True,
                )
            except ClerkErrors as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to create user: {str(e)}",
                )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to find or create user",
            )

        # Create a session for the user
        # Note: sessions.create is for testing only; in production use sign-in tokens
        try:
            session = clerk.sessions.create(request={
                "user_id": user.id,
            })
        except ClerkErrors as e:
            # If sessions.create fails (production), try sign-in tokens
            try:
                sign_in_token = clerk.sign_in_tokens.create(request={
                    "user_id": user.id,
                })
                # Sign-in tokens need to be exchanged by the client
                # For now, return error suggesting alternative approach
                raise HTTPException(
                    status_code=status.HTTP_501_NOT_IMPLEMENTED,
                    detail="Session creation not available in production. Use sign-in tokens.",
                )
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to create session: {str(e)}",
                )

        # Get session token
        token_response = clerk.sessions.create_token(session_id=session.id)
        jwt_token = token_response.jwt if hasattr(token_response, 'jwt') else str(token_response)

        # Get user's organizations
        organizations = await get_user_organizations(clerk, user.id)

        # Build response
        user_email = None
        if hasattr(user, 'email_addresses') and user.email_addresses:
            user_email = user.email_addresses[0].email_address

        return AuthResponse(
            token=jwt_token,
            user=UserResponse(
                id=user.id,
                email=user_email,
                first_name=user.first_name if hasattr(user, 'first_name') else None,
                last_name=user.last_name if hasattr(user, 'last_name') else None,
            ),
            organizations=organizations,
        )


@router.get("/me", response_model=MeResponse)
async def get_current_user_info(current_user: ClerkUser = Depends(get_current_user)):
    """
    Get current authenticated user's info and organizations.
    """
    with get_clerk_client() as clerk:
        # Get full user info from Clerk
        try:
            user = clerk.users.get(user_id=current_user.id)
        except ClerkErrors:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # Get organizations
        organizations = await get_user_organizations(clerk, current_user.id)

        # Build response
        user_email = None
        if hasattr(user, 'email_addresses') and user.email_addresses:
            user_email = user.email_addresses[0].email_address

        return MeResponse(
            user=UserResponse(
                id=user.id,
                email=user_email,
                first_name=user.first_name if hasattr(user, 'first_name') else None,
                last_name=user.last_name if hasattr(user, 'last_name') else None,
            ),
            organizations=organizations,
        )


@router.post("/organizations", response_model=OrganizationResponse)
async def create_organization(
    request: CreateOrganizationRequest,
    current_user: ClerkUser = Depends(get_current_user),
):
    """
    Create a new organization (family) for the current user.
    The user becomes the admin of the organization.
    """
    with get_clerk_client() as clerk:
        try:
            # Create organization with current user as creator
            org = clerk.organizations.create(request={
                "name": request.name,
                "created_by": current_user.id,
            })

            return OrganizationResponse(
                id=org.id,
                name=org.name,
                slug=org.slug if hasattr(org, 'slug') else None,
            )

        except ClerkErrors as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to create organization: {str(e)}",
            )
