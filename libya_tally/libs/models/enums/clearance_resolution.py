from django_enumfield import enum


class ClearanceResolution(enum.Enum):
    PENDING_FIELD_INPUT = 0
    PASS_TO_ADMINISTRATOR = 1
    RESET_TO_PREINTAKE = 2
