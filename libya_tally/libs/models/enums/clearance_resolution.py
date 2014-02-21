from django_enumfield import enum
from django.utils.translation import ugettext_lazy as _

EMPTY_KEY = 0


class ClearanceResolution(enum.Enum):
    PENDING_FIELD_INPUT = 1
    PASS_TO_ADMINISTRATOR = 2
    RESET_TO_PREINTAKE = 3


CLEARANCE_CHOICES = [
    (EMPTY_KEY, '----'),
    (ClearanceResolution.PENDING_FIELD_INPUT, _(u"Pending Field Input")),
    (ClearanceResolution.PASS_TO_ADMINISTRATOR, _(u"Pass To Administrator")),
    (ClearanceResolution.RESET_TO_PREINTAKE, _(u"Reset To Preintake"))
]
