from datetime import datetime

from django.utils.timezone import utc


def now():
    return datetime.utcnow().replace(tzinfo=utc)
