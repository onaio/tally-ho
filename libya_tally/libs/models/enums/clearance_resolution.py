from django_enumfield import enum


class ClearanceResolution(enum.Enum):
    PENDING_FIELD_INPUT = 1
    PASS_TO_ADMINISTRATOR = 2
    RESET_TO_PREINTAKE = 3
