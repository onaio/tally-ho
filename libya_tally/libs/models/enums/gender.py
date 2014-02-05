from django.utils.translation import ugettext as _
from django_enumfield import enum


class Gender(enum.Enum):
    MALE = 0
    FEMALE = 1
    UNISEX = 3

    @classmethod
    def to_name(cls, enum):
        return _('Undefined') if enum is None else dict(cls.choices())[enum]
