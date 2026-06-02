"""
Timestamp and time-related utilities for BRK.

All timestamps are UTC ISO-8601. No local time assumptions.
"""

from __future__ import annotations

from datetime import datetime, timezone


def parse_utc_timestamp(ts_str: str) -> datetime:
    """Parse an ISO-8601 UTC timestamp string.

    Supports:
      - 2026-01-01T00:00:00Z
      - 2026-01-01T00:00:00+00:00

    Returns a timezone-aware datetime in UTC.
    Raises ValueError if the format is unrecognizable.
    """
    s = ts_str.strip()
    # Replace 'Z' suffix with '+00:00' for fromisoformat compatibility
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        raise ValueError(f"Timestamp lacks timezone info: {ts_str!r}")
    return dt.astimezone(timezone.utc)


def format_utc_timestamp(dt: datetime) -> str:
    """Format a datetime as ISO-8601 UTC string with 'Z' suffix.

    Input must be timezone-aware. Output is always UTC.
    """
    if dt.tzinfo is None:
        raise ValueError("Cannot format naive datetime; timezone required")
    utc_dt = dt.astimezone(timezone.utc)
    return utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def now_utc() -> datetime:
    """Return the current UTC datetime."""
    return datetime.now(timezone.utc)


def now_utc_iso() -> str:
    """Return the current UTC timestamp as ISO-8601 string."""
    return format_utc_timestamp(now_utc())


def datetime_to_offset_seconds(dt: datetime, origin: datetime) -> int:
    """Compute offset in seconds from origin to dt.

    Both must be timezone-aware. Returns an integer (truncated).
    """
    delta = dt - origin
    return int(delta.total_seconds())


def offset_seconds_to_datetime(offset_s: int, origin: datetime) -> datetime:
    """Add offset_s seconds to origin datetime."""
    from datetime import timedelta
    return origin + timedelta(seconds=offset_s)
