"""Utility functions for the application."""

from typing import Optional


def format_user_name(first_name: Optional[str], last_name: Optional[str]) -> str:
    """Format a user's name as 'FirstName L.' or fallback to 'Unknown'.

    Args:
        first_name: User's first name (may be None)
        last_name: User's last name (may be None)

    Returns:
        Formatted name like "Alexander B." or just "Alexander" if no last name,
        or "Unknown" if no name available.
    """
    if first_name:
        if last_name:
            return f"{first_name} {last_name[0]}."
        return first_name
    return "Unknown"
