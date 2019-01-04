from django.utils.translation import ugettext_lazy as _

from tally_ho.libs.utils.enum import Enum


class Gender(Enum):
    MALE = 0
    FEMALE = 1
    UNISEX = 3

    CHOICES = [
        (MALE, _(u'Male')),
        (FEMALE, _(u'Female')),
        (UNISEX, _(u'Unisex')),
    ]
