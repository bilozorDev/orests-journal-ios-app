"""Cache key generators and TTL constants."""

# TTL values in seconds
TTL_DASHBOARD = 60          # 1 minute (matches client-side cache)
TTL_TODAY_FEEDINGS = 60     # 1 minute
TTL_FEEDING_HISTORY = 60    # 1 minute (matches client-side cache)
TTL_CALORIE_GOAL = 300      # 5 minutes (rarely changes)
TTL_ACTIVE_MEDS = 600       # 10 minutes
TTL_FOODS = 3600            # 1 hour (organization-wide)
TTL_DOSE_COUNTS = 60        # 1 minute (changes frequently)
TTL_LAST_DOSE = 60          # 1 minute


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


def key_foods(org_id: str) -> str:
    """Cache key for organization foods."""
    return f"foods:{org_id}"


def key_dose_counts(medication_id: str, date: str) -> str:
    """Cache key for today's dose count for a medication."""
    return f"dose_counts:{medication_id}:{date}"


def key_last_dose(medication_id: str) -> str:
    """Cache key for last dose of a medication."""
    return f"last_dose:{medication_id}"


def key_feeding_history(pet_id: str, offset: int, limit: int) -> str:
    """Cache key for paginated feeding history."""
    return f"feeding_history:{pet_id}:{offset}:{limit}"


def key_medications(org_id: str, pet_id: str = None, active_only: bool = False) -> str:
    """Cache key for medications list."""
    if pet_id:
        return f"medications:{org_id}:{pet_id}:{active_only}"
    return f"medications:{org_id}:all:{active_only}"
