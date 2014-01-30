from django_enumfield import enum


class RaceType(enum.Enum):
    GENERAL = 0
    WOMENS = 1
    GENERAL_AND_COMPONENT = 2
