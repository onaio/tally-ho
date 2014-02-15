from django_enumfield import enum


class ActionsPrior(enum.Enum):
    REQUEST_COPY_FROM_FIELD = 0
    REQUEST_AUDIT_ACTION_FROM_FIELD = 1
    PENDING_ADVICE = 2
    NONE_REQUIRED = 3
