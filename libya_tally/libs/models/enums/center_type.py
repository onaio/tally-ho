from django_enumfield import enum


class CenterType(enum.Enum):
    GENERAL = 0
    SPECIAL = 1
