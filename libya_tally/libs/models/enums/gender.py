from django_enumfield import enum


class Gender(enum.Enum):
    MALE = 0
    FEMALE = 1
    UNISEX = 3
