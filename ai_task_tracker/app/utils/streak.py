"""Daily streak calculation utility."""
from datetime import date, timedelta
from typing import List


def calculate_streak(active_dates: List[date]) -> int:
    """
    Calculate the current consecutive-day streak ending today (or yesterday).

    Args:
        active_dates: List of calendar dates on which the user was active.

    Returns:
        Streak length in days.
    """
    if not active_dates:
        return 0

    today = date.today()
    date_set = set(active_dates)

    # Accept streak if user was active today OR yesterday (grace period)
    start = today if today in date_set else today - timedelta(days=1)
    if start not in date_set:
        return 0

    streak = 0
    current = start
    while current in date_set:
        streak += 1
        current -= timedelta(days=1)

    return streak


def calculate_longest_streak(active_dates: List[date]) -> int:
    """Calculate the longest streak ever recorded for the given dates."""
    if not active_dates:
        return 0

    sorted_dates = sorted(set(active_dates))
    longest = 1
    current = 1

    for i in range(1, len(sorted_dates)):
        if (sorted_dates[i] - sorted_dates[i - 1]).days == 1:
            current += 1
            longest = max(longest, current)
        else:
            current = 1

    return longest
