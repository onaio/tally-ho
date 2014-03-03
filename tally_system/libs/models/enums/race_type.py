from django_enumfield import enum


class RaceType(enum.Enum):
    GENERAL = 0
    WOMEN = 1
    COMPONENT_AMAZIGH = 2
    COMPONENT_TWARAG = 3
    COMPONENT_TEBU = 4
