"""
Shared notification utilities for family-related push notifications.
"""
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import FamilyMember
from app.models.notification import UserDeviceToken, NotificationPreference


# Mapping from notification type to preference field name
NOTIFICATION_TYPE_TO_PREF = {
    # Family Updates
    "member_joined": "family_member_joined",
    "role_changed": "family_role_changed",
    "member_left": "family_member_left",
    "member_left_promoted": "family_member_left_promoted",
    "account_deleted": "family_account_deleted",
    "account_deleted_promoted": "family_account_deleted_promoted",
    # Pet Updates
    "pet_added": "pet_added",
    "pet_updated": "pet_updated",
    "pet_deleted": "pet_deleted",
}


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


async def get_filtered_family_member_tokens(
    db: AsyncSession,
    family_id: UUID,
    exclude_user_id: UUID,
    notification_type: str,
) -> list[str]:
    """Get device tokens for family members who have this notification type enabled.

    Args:
        db: Database session
        family_id: The family ID to get members from
        exclude_user_id: User ID to exclude (typically who triggered the action)
        notification_type: The notification type (e.g., 'member_joined', 'pet_added')

    Returns:
        List of active device tokens for members who want this notification type.
    """
    pref_field = NOTIFICATION_TYPE_TO_PREF.get(notification_type)
    if not pref_field:
        # Unknown notification type - fall back to sending to all
        return await get_other_family_member_tokens(db, family_id, exclude_user_id)

    # Get family member user IDs (excluding the triggering user)
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

    # Get preferences for these users - filter out those with this pref disabled
    # Users without a preferences row default to all enabled (don't filter them out)
    prefs_query = select(NotificationPreference.user_id).where(
        and_(
            NotificationPreference.user_id.in_(user_ids),
            getattr(NotificationPreference, pref_field) == False,
        )
    )
    prefs_result = await db.execute(prefs_query)
    disabled_user_ids = set(prefs_result.scalars().all())

    # Filter to users who want this notification
    enabled_user_ids = [uid for uid in user_ids if uid not in disabled_user_ids]

    if not enabled_user_ids:
        return []

    # Get active device tokens for enabled users
    tokens_query = select(UserDeviceToken.device_token).where(
        and_(
            UserDeviceToken.user_id.in_(enabled_user_ids),
            UserDeviceToken.is_active == True,
        )
    )
    tokens_result = await db.execute(tokens_query)
    return list(tokens_result.scalars().all())
