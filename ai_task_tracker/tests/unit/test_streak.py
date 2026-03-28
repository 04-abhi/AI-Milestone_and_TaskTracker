"""Unit tests for streak utility."""
from datetime import date, timedelta
import pytest
from app.utils.streak import calculate_streak, calculate_longest_streak


def _dates_back(n: int):
    """Return last n consecutive dates ending today."""
    today = date.today()
    return [today - timedelta(days=i) for i in range(n)]


def test_empty_dates():
    assert calculate_streak([]) == 0


def test_single_today():
    assert calculate_streak([date.today()]) == 1


def test_consecutive_streak():
    dates = _dates_back(7)
    assert calculate_streak(dates) == 7


def test_broken_streak():
    today = date.today()
    dates = [today, today - timedelta(days=1), today - timedelta(days=3)]
    assert calculate_streak(dates) == 2


def test_streak_grace_period_yesterday():
    """Streak should still count if user was last active yesterday."""
    yesterday = date.today() - timedelta(days=1)
    dates = [yesterday - timedelta(days=i) for i in range(5)]
    assert calculate_streak(dates) == 5


def test_longest_streak():
    today = date.today()
    dates = (
        _dates_back(3)                                          # streak of 3
        + [today - timedelta(days=10 + i) for i in range(7)]   # streak of 7 earlier
    )
    assert calculate_longest_streak(dates) == 7


def test_no_duplicate_counting():
    today = date.today()
    dates = [today, today, today - timedelta(days=1)]
    assert calculate_streak(dates) == 2
