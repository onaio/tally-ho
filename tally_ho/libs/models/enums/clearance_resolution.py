from django_enumfield import enum
from django.utils.translation import ugettext_lazy as _


class ClearanceResolution(enum.Enum):
    EMPTY = 0
    PENDING_FIELD_INPUT = 1
    PASS_TO_ADMINISTRATOR = 2
    RESET_TO_PREINTAKE = 3

    labels = {
        EMPTY: _('Empty'),
        PENDING_FIELD_INPUT: _(u"Pending Field Input"),
        PASS_TO_ADMINISTRATOR: _(u"Pass To Administrator"),
        RESET_TO_PREINTAKE: _(u"Reset To Preintake")
    }

CLEARANCE_CHOICES = [
    (ClearanceResolution.EMPTY, '----'),
    (ClearanceResolution.PENDING_FIELD_INPUT, _(u"Pending Field Input")),
    (ClearanceResolution.PASS_TO_ADMINISTRATOR, _(u"Pass To Administrator")),
    (ClearanceResolution.RESET_TO_PREINTAKE, _(u"Reset To Preintake"))
]
