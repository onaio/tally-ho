from django.utils.translation import gettext_lazy as _

from tally_ho.libs.utils.enum import Enum


class Gender(Enum):
    MALE = 0
    FEMALE = 1
    UNISEX = 3

