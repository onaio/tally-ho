from django_enumfield import enum


class ClearanceResolution(enum.Enum):
    ISSUE_RESOLVED_RESENT = 0
    PENDING_FIELD_INPUT = 1
    PASS_TO_ADMINISTRATOR = 2
    RESET_TO_PREINTAKE = 3
