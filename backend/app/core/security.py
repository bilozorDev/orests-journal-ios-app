from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
import httpx
from pydantic import BaseModel

from app.core.config import get_settings

security = HTTPBearer()


class ClerkUser(BaseModel):
    """Represents the authenticated user from Clerk JWT."""
    id: str  # Clerk user ID
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


# Cache for Clerk JWKS
_jwks_cache: Optional[dict] = None


async def get_clerk_jwks() -> dict:
    """Fetch Clerk's JWKS (JSON Web Key Set) for JWT verification."""
    global _jwks_cache

    if _jwks_cache is not None:
        return _jwks_cache

    settings = get_settings()
    jwks_url = f"{settings.clerk_jwt_issuer}/.well-known/jwks.json"

    async with httpx.AsyncClient() as client:
        response = await client.get(jwks_url)
        response.raise_for_status()
        _jwks_cache = response.json()
        return _jwks_cache


async def verify_clerk_token(token: str) -> dict:
    """Verify a Clerk JWT token and return the claims."""
    settings = get_settings()

    try:
        # Get JWKS
        jwks = await get_clerk_jwks()

        # Get the key ID from the token header
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")

        # Debug: print unverified claims to see issuer
        unverified_claims = jwt.get_unverified_claims(token)
        print(f"Token issuer: {unverified_claims.get('iss')}")
        print(f"Expected issuer: {settings.clerk_jwt_issuer}")
        print(f"Token kid: {kid}")

        # Find the matching key
        rsa_key = None
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                rsa_key = key
                break

        if rsa_key is None:
            print(f"Available keys: {[k.get('kid') for k in jwks.get('keys', [])]}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unable to find appropriate key",
            )

        # Verify and decode the token
        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            issuer=settings.clerk_jwt_issuer,
            options={"verify_aud": False},  # Clerk doesn't always set audience
        )

        return payload

    except JWTError as e:
        print(f"JWT verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> ClerkUser:
    """Dependency to get the current authenticated user from Clerk JWT."""
    token = credentials.credentials

    payload = await verify_clerk_token(token)

    # Extract user info from Clerk JWT claims
    user = ClerkUser(
        id=payload.get("sub"),
        email=payload.get("email"),
        first_name=payload.get("first_name"),
        last_name=payload.get("last_name"),
    )

    return user


async def get_current_user_id(
    user: ClerkUser = Depends(get_current_user),
) -> str:
    """Dependency to get just the current user's ID."""
    return user.id
