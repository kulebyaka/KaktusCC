import re
import hashlib
from datetime import datetime
import pytz
from typing import Optional
import logging

logger = logging.getLogger(__name__)

def parse_czech_datetime(title: str, timezone: str = 'Europe/Prague') -> Optional[datetime]:
    """Parse Czech date format from event title.

    Handles formats like:
    - "15.10.2025 15:00" (no spaces after dots)
    - "15. 10. 2025 15:00" (spaces after dots)
    - "Dobíječka 15. 10. 2025 15:00 - 17:00" (full event title)
    """
    # Pattern that handles optional spaces after dots
    pattern = r'(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})\s+(\d{1,2}):(\d{2})'
    match = re.search(pattern, title)

    if not match:
        logger.warning(f"Could not parse datetime from title: {title[:100]}")
        return None

    try:
        day, month, year, hour, minute = map(int, match.groups())

        prague_tz = pytz.timezone(timezone)
        dt = datetime(year, month, day, hour, minute)
        localized_dt = prague_tz.localize(dt)

        logger.info(f"Parsed datetime: {localized_dt}")
        return localized_dt

    except ValueError as e:
        logger.error(f"Error parsing datetime from {title[:100]}: {e}")
        return None

def calculate_post_hash(title: str, content: str) -> str:
    """Calculate SHA256 hash for post deduplication."""
    combined = f"{title.strip()}{content.strip()}"
    return hashlib.sha256(combined.encode('utf-8')).hexdigest()

def datetime_to_unix_timestamp(dt: datetime) -> int:
    """Convert datetime to Unix timestamp for Telegram API."""
    if dt.tzinfo is None:
        logger.warning("Datetime has no timezone info, assuming UTC")
        dt = pytz.UTC.localize(dt)
    
    return int(dt.timestamp())

def is_valid_schedule_time(dt: datetime) -> bool:
    """Check if datetime is valid for Telegram scheduling (10s - 365 days from now)."""
    now = datetime.now(pytz.UTC)

    if dt.tzinfo is None:
        dt = pytz.UTC.localize(dt)
    else:
        dt = dt.astimezone(pytz.UTC)

    time_diff = (dt - now).total_seconds()

    return 10 <= time_diff <= 365 * 24 * 3600

def escape_markdown(text: str) -> str:
    """Escape special characters for Telegram Markdown format.

    Escapes: _ * [ ] ( ) ~ ` > # + - = | { } . !

    Args:
        text: Text to escape

    Returns:
        Escaped text safe for Markdown parsing
    """
    if not text:
        return text

    # Characters that need to be escaped in Telegram Markdown
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']

    escaped_text = text
    for char in special_chars:
        escaped_text = escaped_text.replace(char, f'\\{char}')

    return escaped_text