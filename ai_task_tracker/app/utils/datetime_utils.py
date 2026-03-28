"""Datetime helper utilities."""
from datetime import date, datetime, timezone
from typing import Optional
import pytz


def utcnow() -> datetime:
    """Return timezone-aware UTC now."""
    return datetime.now(timezone.utc)


def to_user_timezone(dt: Optional[datetime], tz_name: str) -> Optional[datetime]:
    """Convert a UTC datetime to the user's local timezone."""
    if dt is None:
        return None
    try:
        tz = pytz.timezone(tz_name)
        return dt.astimezone(tz)
    except Exception:
        return dt


def start_of_day(d: Optional[date] = None) -> datetime:
    """Return midnight UTC for the given date (default today)."""
    d = d or date.today()
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)


def is_overdue(due_date: Optional[datetime]) -> bool:
    if due_date is None:
        return False
    return due_date < utcnow()


def humanize_delta(dt: datetime) -> str:
    """Return a human-friendly relative time string."""
    now = utcnow()
    delta = now - dt
    seconds = int(delta.total_seconds())
    if seconds < 60:
        return "just now"
    if seconds < 3600:
        return f"{seconds // 60}m ago"
    if seconds < 86400:
        return f"{seconds // 3600}h ago"
    return f"{delta.days}d ago"
