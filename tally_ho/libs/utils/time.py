from datetime import datetime, timezone


def now():
    return datetime.utcnow().replace(tzinfo=timezone.utc)
