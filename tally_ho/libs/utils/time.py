from datetime import datetime, timezone


def now():
    return datetime.utcnow().replace(tzinfo=timezone.utc)


def format_duration_human_readable(duration):
    """
    Format a timedelta duration into a human-readable string.

    Args:
        duration: A timedelta object

    Returns:
        A string like "2d 1h 3m" or "1h 30m" or "45m" or "30s"
        Returns None if duration is None
    """
    if duration is None:
        return None

    total_seconds = int(duration.total_seconds())

    # Use divmod for cleaner calculation
    days, remainder = divmod(total_seconds, 86400)  # 86400 seconds in a day
    hours, remainder = divmod(remainder, 3600)      # 3600 seconds in an hour
    minutes, seconds = divmod(remainder, 60)        # 60 seconds in a minute

    if days > 0:
        return f"{days}d {hours}h {minutes}m"
    elif hours > 0:
        return f"{hours}h {minutes}m"
    elif minutes > 0:
        return f"{minutes}m"
    else:
        return f"{seconds}s"
