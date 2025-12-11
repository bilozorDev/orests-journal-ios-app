#!/usr/bin/env python3
"""
CLI script to create a test user and add them to a family via invite code.

Usage:
    python scripts/add_test_user.py <invite_code>
    python scripts/add_test_user.py <invite_code> --email test@example.com --name "John Doe"

This will:
1. Create a new test user (or use existing if email matches)
2. Join the family using the invite code
3. Trigger the "member joined" notification to existing family members
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import os
from typing import Optional
from uuid import uuid4

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core.config import get_settings
from app.models.user import User, Family, FamilyMember
from app.models.notification import UserDeviceToken
from app.services.apns import apns_service
from app.cache.helpers import cache_delete
from app.cache.keys import key_family_detail


async def get_db_session() -> AsyncSession:
    """Create a database session."""
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    return session_factory()


async def find_or_create_user(db: AsyncSession, email: str, first_name: str, last_name: str | None) -> User:
    """Find existing user by email or create a new one."""
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user:
        print(f"Found existing user: {user.email} (ID: {user.id})")
        return user

    user = User(
        id=uuid4(),
        apple_user_id=f"test_{uuid4().hex[:16]}",  # Fake Apple ID
        email=email,
        first_name=first_name,
        last_name=last_name,
    )
    db.add(user)
    await db.flush()
    print(f"Created new user: {user.email} (ID: {user.id})")
    return user


async def find_family_by_invite_code(db: AsyncSession, invite_code: str) -> Family | None:
    """Find a family by invite code."""
    result = await db.execute(
        select(Family).where(Family.invite_code == invite_code.upper())
    )
    return result.scalar_one_or_none()


async def is_member(db: AsyncSession, family_id, user_id) -> bool:
    """Check if user is already a member of the family."""
    result = await db.execute(
        select(FamilyMember).where(
            FamilyMember.family_id == family_id,
            FamilyMember.user_id == user_id,
        )
    )
    return result.scalar_one_or_none() is not None


async def get_other_family_member_tokens(db: AsyncSession, family_id, exclude_user_id) -> list[str]:
    """Get device tokens for family members except the specified user."""
    # Get other family members
    members_result = await db.execute(
        select(FamilyMember.user_id).where(
            FamilyMember.family_id == family_id,
            FamilyMember.user_id != exclude_user_id,
        )
    )
    user_ids = list(members_result.scalars().all())

    if not user_ids:
        return []

    # Get their device tokens
    tokens_result = await db.execute(
        select(UserDeviceToken.device_token).where(
            UserDeviceToken.user_id.in_(user_ids),
            UserDeviceToken.is_active == True,
        )
    )
    return list(tokens_result.scalars().all())


async def join_family(db: AsyncSession, family: Family, user: User) -> bool:
    """Add user to family and send notification."""
    # Check if already a member
    if await is_member(db, family.id, user.id):
        print(f"User {user.email} is already a member of {family.name}")
        return False

    # Add as member
    membership = FamilyMember(
        family_id=family.id,
        user_id=user.id,
        role="member",
    )
    db.add(membership)
    await db.commit()
    print(f"Added {user.email} to family '{family.name}' as member")

    # Invalidate Redis cache for this family
    await cache_delete(key_family_detail(str(family.id)))
    print(f"Invalidated Redis cache for family {family.id}")

    # Send notification to other family members
    member_name = user.first_name or user.email.split("@")[0] if user.email else "Someone"
    tokens = await get_other_family_member_tokens(db, family.id, user.id)

    if tokens:
        print(f"Sending notification to {len(tokens)} device(s)...")
        if apns_service.is_configured:
            sent_count = await apns_service.send_to_multiple(
                device_tokens=tokens,
                title=f"{member_name} joined {family.name}",
                body="A new member has joined your family",
                data={
                    "type": "member_joined",
                    "family_id": str(family.id),
                    "user_id": str(user.id),
                },
            )
            print(f"Notification sent to {sent_count}/{len(tokens)} devices")
        else:
            print("APNs not configured - skipping notification")
    else:
        print("No other family members have registered devices")

    return True


async def main():
    parser = argparse.ArgumentParser(
        description="Create a test user and add them to a family via invite code"
    )
    parser.add_argument("invite_code", help="Family invite code (e.g., ABC12345)")
    parser.add_argument("--email", default=None, help="User email (default: test_<random>@example.com)")
    parser.add_argument("--name", default="Test User", help="User full name (default: Test User)")

    args = parser.parse_args()

    # Parse name
    name_parts = args.name.split(" ", 1)
    first_name = name_parts[0]
    last_name = name_parts[1] if len(name_parts) > 1 else None

    # Generate email if not provided
    email = args.email or f"test_{uuid4().hex[:8]}@example.com"

    print(f"\n{'='*50}")
    print("Add Test User to Family")
    print(f"{'='*50}")
    print(f"Invite Code: {args.invite_code.upper()}")
    print(f"Email: {email}")
    print(f"Name: {first_name} {last_name or ''}")
    print(f"{'='*50}\n")

    db = await get_db_session()

    try:
        # Find family
        family = await find_family_by_invite_code(db, args.invite_code)
        if not family:
            print(f"Error: No family found with invite code '{args.invite_code}'")
            sys.exit(1)

        print(f"Found family: {family.name} (ID: {family.id})")

        # Find or create user
        user = await find_or_create_user(db, email, first_name, last_name)

        # Join family
        await join_family(db, family, user)

        print(f"\n{'='*50}")
        print("Done!")
        print(f"{'='*50}\n")

    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
