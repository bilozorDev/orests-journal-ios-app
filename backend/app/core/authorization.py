"""
Authorization helpers for verifying user access to resources.

These functions prevent IDOR (Insecure Direct Object Reference) vulnerabilities
by verifying that the authenticated user has access to the requested resource
through family membership.

Additionally, these functions set up Row-Level Security (RLS) context by
setting the app.current_user_id session variable, which enables database-level
access control as a defense-in-depth measure.
"""
from uuid import UUID
from typing import Optional, Union

from fastapi import HTTPException, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import set_rls_user
from app.models.user import FamilyMember
from app.models.pet import Pet
from app.models.food import PetFood, PetFeeding, PetCalorieGoal
from app.models.medication import PetMedication, PetMedicationDose
from app.models.health import PetHealthCategory, PetHealthEvent


async def verify_family_access(
    db: AsyncSession,
    user_id: str,
    family_id: Union[str, UUID],
) -> FamilyMember:
    """
    Verify that the user belongs to the specified family.

    Also sets up Row-Level Security (RLS) context for defense-in-depth.

    Args:
        db: Database session
        user_id: The authenticated user's ID
        family_id: The family ID to check access for (string or UUID)

    Returns:
        The FamilyMember record if access is granted

    Raises:
        HTTPException 403: If user does not belong to the family
    """
    # Set RLS context for defense-in-depth
    await set_rls_user(db, user_id)

    # Handle both string and UUID inputs
    user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
    family_uuid = UUID(str(family_id)) if not isinstance(family_id, UUID) else family_id

    query = select(FamilyMember).where(
        and_(
            FamilyMember.user_id == user_uuid,
            FamilyMember.family_id == family_uuid
        )
    )
    result = await db.execute(query)
    membership = result.scalar_one_or_none()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: you are not a member of this family"
        )

    return membership


async def verify_admin_access(
    db: AsyncSession,
    user_id: str,
    family_id: Union[str, UUID],
) -> FamilyMember:
    """
    Verify that the user is an admin of the specified family.

    Args:
        db: Database session
        user_id: The authenticated user's ID
        family_id: The family ID to check access for

    Returns:
        The FamilyMember record if user is admin

    Raises:
        HTTPException 403: If user is not an admin of the family
    """
    membership = await verify_family_access(db, user_id, family_id)

    if membership.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: admin privileges required"
        )

    return membership


async def verify_pet_access(
    db: AsyncSession,
    user_id: str,
    pet_id: UUID,
) -> Pet:
    """
    Verify that the user has access to the specified pet through family membership.

    Also sets up Row-Level Security (RLS) context for defense-in-depth.

    Args:
        db: Database session
        user_id: The authenticated user's ID
        pet_id: The pet ID to check access for

    Returns:
        The Pet record if access is granted

    Raises:
        HTTPException 404: If pet does not exist
        HTTPException 403: If user does not have access to the pet
    """
    # Set RLS context for defense-in-depth
    await set_rls_user(db, user_id)

    query = select(Pet).where(Pet.id == pet_id)
    result = await db.execute(query)
    pet = result.scalar_one_or_none()

    if not pet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pet not found"
        )

    # Verify user belongs to the pet's family (RLS context already set)
    await verify_family_access(db, user_id, pet.family_id)

    return pet


async def verify_food_access(
    db: AsyncSession,
    user_id: str,
    food_id: UUID,
) -> PetFood:
    """
    Verify that the user has access to the specified food through family membership.

    Also sets up Row-Level Security (RLS) context for defense-in-depth.

    Args:
        db: Database session
        user_id: The authenticated user's ID
        food_id: The food ID to check access for

    Returns:
        The PetFood record if access is granted

    Raises:
        HTTPException 404: If food does not exist
        HTTPException 403: If user does not have access to the food
    """
    # Set RLS context for defense-in-depth
    await set_rls_user(db, user_id)

    query = select(PetFood).where(PetFood.id == food_id)
    result = await db.execute(query)
    food = result.scalar_one_or_none()

    if not food:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Food not found"
        )

    # Verify user belongs to the food's family
    await verify_family_access(db, user_id, food.family_id)

    return food


async def verify_feeding_access(
    db: AsyncSession,
    user_id: str,
    feeding_id: UUID,
) -> PetFeeding:
    """
    Verify that the user has access to the specified feeding through family membership.

    Args:
        db: Database session
        user_id: The authenticated user's ID
        feeding_id: The feeding ID to check access for

    Returns:
        The PetFeeding record if access is granted

    Raises:
        HTTPException 404: If feeding does not exist
        HTTPException 403: If user does not have access to the feeding
    """
    query = select(PetFeeding).where(PetFeeding.id == feeding_id)
    result = await db.execute(query)
    feeding = result.scalar_one_or_none()

    if not feeding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feeding record not found"
        )

    # Get the pet to check family access
    pet = await verify_pet_access(db, user_id, feeding.pet_id)

    return feeding


async def verify_calorie_goal_access(
    db: AsyncSession,
    user_id: str,
    goal_id: UUID,
) -> PetCalorieGoal:
    """
    Verify that the user has access to the specified calorie goal.

    Args:
        db: Database session
        user_id: The authenticated user's ID
        goal_id: The calorie goal ID to check access for

    Returns:
        The PetCalorieGoal record if access is granted

    Raises:
        HTTPException 404: If goal does not exist
        HTTPException 403: If user does not have access
    """
    query = select(PetCalorieGoal).where(PetCalorieGoal.id == goal_id)
    result = await db.execute(query)
    goal = result.scalar_one_or_none()

    if not goal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Calorie goal not found"
        )

    # Get the pet to check family access
    await verify_pet_access(db, user_id, goal.pet_id)

    return goal


async def verify_medication_access(
    db: AsyncSession,
    user_id: str,
    medication_id: UUID,
) -> PetMedication:
    """
    Verify that the user has access to the specified medication.

    Args:
        db: Database session
        user_id: The authenticated user's ID
        medication_id: The medication ID to check access for

    Returns:
        The PetMedication record if access is granted

    Raises:
        HTTPException 404: If medication does not exist
        HTTPException 403: If user does not have access
    """
    query = select(PetMedication).where(PetMedication.id == medication_id)
    result = await db.execute(query)
    medication = result.scalar_one_or_none()

    if not medication:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medication not found"
        )

    # Get the pet to check family access
    await verify_pet_access(db, user_id, medication.pet_id)

    return medication


async def verify_dose_access(
    db: AsyncSession,
    user_id: str,
    dose_id: UUID,
) -> PetMedicationDose:
    """
    Verify that the user has access to the specified medication dose.

    Args:
        db: Database session
        user_id: The authenticated user's ID
        dose_id: The dose ID to check access for

    Returns:
        The PetMedicationDose record if access is granted

    Raises:
        HTTPException 404: If dose does not exist
        HTTPException 403: If user does not have access
    """
    query = select(PetMedicationDose).where(PetMedicationDose.id == dose_id)
    result = await db.execute(query)
    dose = result.scalar_one_or_none()

    if not dose:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medication dose not found"
        )

    # Get the medication to check access (which will check pet -> family)
    await verify_medication_access(db, user_id, dose.medication_id)

    return dose


async def verify_health_category_access(
    db: AsyncSession,
    user_id: str,
    category_id: UUID,
) -> PetHealthCategory:
    """
    Verify that the user has access to the specified health category.

    Args:
        db: Database session
        user_id: The authenticated user's ID
        category_id: The health category ID to check access for

    Returns:
        The PetHealthCategory record if access is granted

    Raises:
        HTTPException 404: If category does not exist
        HTTPException 403: If user does not have access
    """
    query = select(PetHealthCategory).where(PetHealthCategory.id == category_id)
    result = await db.execute(query)
    category = result.scalar_one_or_none()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Health category not found"
        )

    # Verify user has access to this family
    await verify_family_access(db, user_id, str(category.family_id))

    return category


async def verify_health_event_access(
    db: AsyncSession,
    user_id: str,
    event_id: UUID,
) -> PetHealthEvent:
    """
    Verify that the user has access to the specified health event.

    Args:
        db: Database session
        user_id: The authenticated user's ID
        event_id: The health event ID to check access for

    Returns:
        The PetHealthEvent record if access is granted

    Raises:
        HTTPException 404: If event does not exist
        HTTPException 403: If user does not have access
    """
    query = select(PetHealthEvent).where(PetHealthEvent.id == event_id)
    result = await db.execute(query)
    event = result.scalar_one_or_none()

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Health event not found"
        )

    # Verify access via the pet (events have pet_id directly)
    await verify_pet_access(db, user_id, event.pet_id)

    return event
