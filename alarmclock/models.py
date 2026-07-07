from __future__ import annotations

import uuid
from dataclasses import dataclass, field


def validate_time(raw: str) -> str:
    """
    Validate and normalize a time string to 'HH:MM' 24-hour format.

    Args:
        raw: Time string in "H:MM" or "HH:MM" format.

    Returns:
        Normalized time string as "HH:MM".

    Raises:
        ValueError: If time is invalid or out of range.
    """
    raw = raw.strip()

    # Check basic format: must contain exactly one colon
    if raw.count(':') != 1:
        raise ValueError("Time must be HH:MM in 24-hour format, e.g. 07:30")

    parts = raw.split(':')
    hours_str, minutes_str = parts[0], parts[1]

    # Validate that both parts are non-empty and numeric
    if not hours_str or not minutes_str:
        raise ValueError("Time must be HH:MM in 24-hour format, e.g. 07:30")

    if not hours_str.isdigit() or not minutes_str.isdigit():
        raise ValueError("Time must be HH:MM in 24-hour format, e.g. 07:30")

    # Parse and validate ranges
    try:
        hours = int(hours_str)
        minutes = int(minutes_str)
    except ValueError:
        raise ValueError("Time must be HH:MM in 24-hour format, e.g. 07:30")

    if not (0 <= hours <= 23):
        raise ValueError("Time must be HH:MM in 24-hour format, e.g. 07:30")

    if not (0 <= minutes <= 59):
        raise ValueError("Time must be HH:MM in 24-hour format, e.g. 07:30")

    # Return normalized format
    return f"{hours:02d}:{minutes:02d}"


def new_id() -> str:
    """
    Generate a new alarm ID using UUID hex, truncated to 8 characters.

    Returns:
        8-character hex string.
    """
    return uuid.uuid4().hex[:8]


# Weekday codes in order: index 0 = Monday (matching Python's time.localtime().tm_wday)
DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def validate_repeat(raw: str) -> list[str]:
    """
    Validate and normalize a repeat specification to a list of day codes.

    Accepts case-insensitive, whitespace-tolerant input:
    - "", "once", "one", "no", "none", "off"  -> [] (one-time alarm)
    - "daily", "everyday", "every day", "all"  -> full week
    - "weekdays", "weekday"  -> Monday-Friday
    - "weekends", "weekend"  -> Saturday-Sunday
    - Comma- and/or space-separated day names/abbreviations (e.g., "mon,wed,fri")

    Returns:
        List of day codes from DAYS, deduplicated and sorted in DAYS order.

    Raises:
        ValueError: If an unrecognized token is provided.
    """
    raw = raw.strip().lower()

    # Handle empty or explicit one-time specifications
    if not raw or raw in ("once", "one", "no", "none", "off"):
        return []

    # Handle all-week specifications
    if raw in ("daily", "everyday", "every day", "all"):
        return DAYS.copy()

    # Handle weekday shortcuts
    if raw in ("weekdays", "weekday"):
        return DAYS[:5]  # mon-fri

    if raw in ("weekends", "weekend"):
        return DAYS[5:]  # sat-sun

    # Parse comma- and/or space-separated day tokens
    # Replace commas with spaces, then split on whitespace
    normalized = raw.replace(",", " ")
    tokens = normalized.split()

    # Map of day name/abbreviation to day code
    day_map = {
        "monday": "mon",
        "mon": "mon",
        "tuesday": "tue",
        "tues": "tue",
        "tue": "tue",
        "wednesday": "wed",
        "wed": "wed",
        "thursday": "thu",
        "thurs": "thu",
        "thur": "thu",
        "thu": "thu",
        "friday": "fri",
        "fri": "fri",
        "saturday": "sat",
        "sat": "sat",
        "sunday": "sun",
        "sun": "sun",
    }

    result_set = set()
    for token in tokens:
        if token not in day_map:
            raise ValueError(
                "Repeat must be once/daily/weekdays/weekends or days like mon,wed,fri"
            )
        result_set.add(day_map[token])

    # Sort into DAYS order
    return sorted(result_set, key=lambda d: DAYS.index(d))


def describe_repeat(repeat: list[str]) -> str:
    """
    Convert a repeat list to a human-readable description.

    Args:
        repeat: List of day codes from DAYS.

    Returns:
        Human-readable string representation.
    """
    if not repeat:
        return "once"

    if len(repeat) == 7 and repeat == DAYS:
        return "daily"

    if repeat == DAYS[:5]:
        return "weekdays"

    if repeat == DAYS[5:]:
        return "weekends"

    # Capitalize and join with commas in DAYS order
    capitalized = [d.capitalize() for d in repeat]
    return ",".join(capitalized)


@dataclass
class Alarm:
    """
    Represents an alarm clock entry.

    Attributes:
        id: Unique identifier for the alarm.
        time: Alarm time in 'HH:MM' 24-hour format.
        label: Human-readable description of the alarm.
        enabled: Whether the alarm is active (default: True).
        repeat: List of day codes for recurring alarms (default: [] for one-time).
        snooze_until: Epoch timestamp (float) for snooze, or None if not snoozed (default: None).
    """
    id: str
    time: str
    label: str
    enabled: bool = True
    repeat: list[str] = field(default_factory=list)
    snooze_until: float | None = None

    def to_dict(self) -> dict:
        """
        Convert the Alarm to a dictionary.

        Returns:
            Dictionary with keys: id, time, label, enabled, repeat, snooze_until.
        """
        return {
            'id': self.id,
            'time': self.time,
            'label': self.label,
            'enabled': self.enabled,
            'repeat': self.repeat,
            'snooze_until': self.snooze_until,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Alarm:
        """
        Create an Alarm from a dictionary.

        Tolerates missing fields for backward compatibility with old JSON:
        - 'label' defaults to "".
        - 'enabled' defaults to True.
        - 'repeat' defaults to [] (coerced to [] if not a list).
        - 'snooze_until' defaults to None.

        Args:
            d: Dictionary with keys: id, time, and optionally label, enabled, repeat, snooze_until.

        Returns:
            An Alarm instance.
        """
        repeat = d.get('repeat', [])
        # Coerce to list if not already a list (backward compatibility)
        if not isinstance(repeat, list):
            repeat = []

        return cls(
            id=d['id'],
            time=d['time'],
            label=d.get('label', ''),
            enabled=d.get('enabled', True),
            repeat=repeat,
            snooze_until=d.get('snooze_until', None),
        )
