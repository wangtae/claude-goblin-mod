"""
Timezone utilities for converting UTC timestamps to local timezone.

Supports auto-detection of system timezone and manual timezone selection.
All data is stored in UTC and converted to local timezone only for display.
"""
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional


def get_system_timezone() -> str:
    """
    Get the system's timezone name.

    Returns:
        IANA timezone name (e.g., 'Asia/Seoul', 'America/New_York')
    """
    def _is_valid_tz(tz_name: str) -> bool:
        """Check if timezone name is valid."""
        try:
            ZoneInfo(tz_name)
            return True
        except:
            return False

    try:
        # Try to get timezone from environment variable first
        import os
        tz_env = os.environ.get('TZ')
        if tz_env and _is_valid_tz(tz_env):
            return tz_env

        # Try to read from /etc/timezone (Linux)
        try:
            with open('/etc/timezone', 'r') as f:
                tz_file = f.read().strip()
                if tz_file and _is_valid_tz(tz_file):
                    return tz_file
        except:
            pass

        # Get system timezone from datetime
        local_tz = datetime.now().astimezone().tzinfo
        if local_tz and hasattr(local_tz, 'key'):
            return local_tz.key

        # Fallback: if str(local_tz) is not a valid IANA name, use UTC
        tz_str = str(local_tz)
        if _is_valid_tz(tz_str):
            return tz_str

        return 'UTC'
    except Exception:
        # Ultimate fallback
        return 'UTC'


def get_user_timezone() -> str:
    """
    Get the user's configured timezone from database.

    Returns:
        IANA timezone name or 'auto' for system detection
    """
    try:
        from src.storage.snapshot_db import load_user_preferences
        prefs = load_user_preferences()
        tz_setting = prefs.get('timezone', 'auto')

        # If auto, return system timezone
        if tz_setting == 'auto':
            return get_system_timezone()

        return tz_setting
    except Exception:
        # Fallback to system timezone
        return get_system_timezone()


def get_timezone_info(tz_name: str) -> dict:
    """
    Get timezone information including offset.

    Args:
        tz_name: IANA timezone name

    Returns:
        Dictionary with timezone info:
        - name: IANA name (e.g., 'Asia/Seoul')
        - offset: UTC offset string (e.g., 'UTC+9')
        - abbr: Timezone abbreviation (e.g., 'KST')
    """
    try:
        tz = ZoneInfo(tz_name)
        now = datetime.now(tz)

        # Get UTC offset
        offset = now.strftime('%z')  # Format: +0900
        offset_hours = int(offset[:3])  # +09
        offset_mins = int(offset[0] + offset[3:5])  # +00

        if offset_mins == 0:
            offset_str = f"UTC{offset_hours:+d}"
        else:
            offset_str = f"UTC{offset_hours:+d}:{abs(offset_mins):02d}"

        # Get timezone abbreviation
        abbr = now.strftime('%Z')

        return {
            'name': tz_name,
            'offset': offset_str,
            'abbr': abbr,
        }
    except Exception:
        return {
            'name': tz_name,
            'offset': 'UTC+0',
            'abbr': 'UTC',
        }


def convert_to_local(utc_datetime: datetime, tz_name: Optional[str] = None) -> datetime:
    """
    Convert UTC datetime to local timezone.

    Args:
        utc_datetime: Datetime in UTC (timezone-aware or naive)
        tz_name: Optional timezone name (uses user preference if not provided)

    Returns:
        Datetime in local timezone
    """
    try:
        # Get timezone
        if tz_name is None:
            tz_name = get_user_timezone()

        tz = ZoneInfo(tz_name)

        # Ensure datetime is timezone-aware (assume UTC if naive)
        if utc_datetime.tzinfo is None:
            utc_datetime = utc_datetime.replace(tzinfo=ZoneInfo('UTC'))

        # Convert to local timezone
        return utc_datetime.astimezone(tz)
    except Exception:
        # Fallback: return as-is
        return utc_datetime


def format_local_time(utc_datetime: datetime, format_string: str, tz_name: Optional[str] = None) -> str:
    """
    Convert UTC datetime to local timezone and format it.

    Args:
        utc_datetime: Datetime in UTC
        format_string: strftime format string (e.g., '%H:%M', '%Y-%m-%d %H:%M:%S')
        tz_name: Optional timezone name (uses user preference if not provided)

    Returns:
        Formatted time string in local timezone
    """
    try:
        local_dt = convert_to_local(utc_datetime, tz_name)
        return local_dt.strftime(format_string)
    except Exception:
        # Fallback: format as-is
        return utc_datetime.strftime(format_string)


def list_common_timezones() -> list[dict]:
    """
    Get list of commonly used timezones for UI selection.

    Returns:
        List of dictionaries with timezone info
    """
    common_tzs = [
        'UTC',
        'Asia/Seoul',
        'Asia/Tokyo',
        'Asia/Shanghai',
        'Asia/Hong_Kong',
        'Asia/Singapore',
        'Europe/London',
        'Europe/Paris',
        'Europe/Berlin',
        'America/New_York',
        'America/Los_Angeles',
        'America/Chicago',
        'Australia/Sydney',
    ]

    return [get_timezone_info(tz) for tz in common_tzs]


def validate_timezone(tz_name: str) -> bool:
    """
    Check if a timezone name is valid.

    Args:
        tz_name: IANA timezone name to validate

    Returns:
        True if valid, False otherwise
    """
    if tz_name == 'auto':
        return True

    try:
        ZoneInfo(tz_name)
        return True
    except Exception:
        return False
