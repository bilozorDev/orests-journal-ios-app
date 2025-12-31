"""Cache key generators and TTL constants."""

# TTL values in seconds
TTL_DASHBOARD = 60          # 1 minute (matches client-side cache)
TTL_TODAY_FEEDINGS = 60     # 1 minute
TTL_FEEDING_HISTORY = 60    # 1 minute (matches client-side cache)
TTL_CALORIE_GOAL = 300      # 5 minutes (rarely changes)
TTL_ACTIVE_MEDS = 600       # 10 minutes
TTL_FOODS = 3600            # 1 hour (family-wide)
TTL_DOSE_COUNTS = 60        # 1 minute (changes frequently)
TTL_LAST_DOSE = 60          # 1 minute
TTL_FAMILY = 300            # 5 minutes (family details with members)
TTL_PETS = 300              # 5 minutes (matches iOS petsCacheTTL)
TTL_HEALTH_EVENTS = 300     # 5 minutes (matches iOS healthCacheTTL)
TTL_HEALTH_CATEGORIES = 300 # 5 minutes (categories rarely change)


def key_dashboard(pet_id: str, date: str) -> str:
    """Cache key for dashboard data. Date ensures cache expires at midnight."""
    return f"dashboard:{pet_id}:{date}"


def key_today_feedings(pet_id: str, date: str) -> str:
    """Cache key for today's feedings."""
    return f"today_feedings:{pet_id}:{date}"


def key_calorie_goal(pet_id: str) -> str:
    """Cache key for active calorie goal."""
    return f"calorie_goal:{pet_id}"


def key_active_meds(pet_id: str, date: str) -> str:
    """Cache key for active medications."""
    return f"active_meds:{pet_id}:{date}"


def key_foods(family_id: str) -> str:
    """Cache key for family foods."""
    return f"foods:{family_id}"


def key_dose_counts(medication_id: str, date: str) -> str:
    """Cache key for today's dose count for a medication."""
    return f"dose_counts:{medication_id}:{date}"


def key_last_dose(medication_id: str) -> str:
    """Cache key for last dose of a medication."""
    return f"last_dose:{medication_id}"


def key_today_doses(medication_id: str, date: str, timezone: str) -> str:
    """Cache key for today's doses for a medication.

    Args:
        medication_id: The medication UUID
        date: The local date string (YYYY-MM-DD)
        timezone: The IANA timezone (e.g., America/Los_Angeles)
    """
    return f"today_doses:{medication_id}:{date}:{timezone}"


def key_feeding_history(pet_id: str, offset: int, limit: int) -> str:
    """Cache key for paginated feeding history."""
    return f"feeding_history:{pet_id}:{offset}:{limit}"


def key_medications(
    family_id: str,
    pet_id: str = None,
    active_only: bool = False,
    include_archived: bool = False,
    offset: int = 0,
    limit: int = 100,
) -> str:
    """Cache key for medications list."""
    pet_part = pet_id if pet_id else "all"
    return f"medications:{family_id}:{pet_part}:{active_only}:{include_archived}:{offset}:{limit}"


def key_all_doses(family_id: str, pet_id: str = None, offset: int = 0, limit: int = 50) -> str:
    """Cache key for all doses history."""
    if pet_id:
        return f"all_doses:{family_id}:{pet_id}:{offset}:{limit}"
    return f"all_doses:{family_id}:all:{offset}:{limit}"


def key_family_detail(family_id: str) -> str:
    """Cache key for family details including members."""
    return f"family:{family_id}"


def key_pets(family_id: str) -> str:
    """Cache key for family pets list."""
    return f"pets:{family_id}"


def key_health_events(pet_id: str, offset: int = 0, limit: int = 100) -> str:
    """Cache key for paginated health events list.

    Note: Only caches unfiltered requests (no category/date filters).
    Filtered requests bypass cache.
    """
    return f"health_events:{pet_id}:{offset}:{limit}"


def key_health_categories(family_id: str) -> str:
    """Cache key for family-wide health categories."""
    return f"health_categories:{family_id}"
