"""
Shared notification utilities for family-related push notifications.
"""
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import FamilyMember
from app.models.notification import UserDeviceToken


async def get_other_family_member_tokens(
    db: AsyncSession,
    family_id: UUID,
    exclude_user_id: UUID,
) -> list[str]:
    """Get active device tokens for family members except the specified user.

    Args:
        db: Database session
        family_id: The family ID to get members from
        exclude_user_id: User ID to exclude (typically the user who triggered the action)

    Returns:
        List of active APNs device tokens for other family members
    """
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

    # Get active device tokens for these users
    tokens_query = select(UserDeviceToken.device_token).where(
        and_(
            UserDeviceToken.user_id.in_(user_ids),
            UserDeviceToken.is_active == True,
        )
    )
    tokens_result = await db.execute(tokens_query)
    return list(tokens_result.scalars().all())


async def get_all_family_member_tokens(
    db: AsyncSession,
    family_id: UUID,
) -> list[str]:
    """Get active device tokens for all family members.

    Args:
        db: Database session
        family_id: The family ID to get members from

    Returns:
        List of active APNs device tokens for all family members
    """
    # Get all family member user IDs
    members_query = select(FamilyMember.user_id).where(
        FamilyMember.family_id == family_id
    )
    members_result = await db.execute(members_query)
    user_ids = list(members_result.scalars().all())

    if not user_ids:
        return []

    # Get active device tokens for these users
    tokens_query = select(UserDeviceToken.device_token).where(
        and_(
            UserDeviceToken.user_id.in_(user_ids),
            UserDeviceToken.is_active == True,
        )
    )
    tokens_result = await db.execute(tokens_query)
    return list(tokens_result.scalars().all())
