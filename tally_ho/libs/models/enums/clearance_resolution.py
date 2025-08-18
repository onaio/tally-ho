from django.utils.translation import gettext_lazy as _

from tally_ho.libs.utils.enum import Enum


class ClearanceResolution(Enum):
    EMPTY = 0
    PENDING_FIELD_INPUT = 1
    PASS_TO_ADMINISTRATOR = 2
    RESET_TO_PREINTAKE = 3
    RESET_TO_PREINTAKE_AND_SKIP_ALL_ZERO_VOTES_CHECK = 4

    CHOICES = [
        (EMPTY, '----'),
        (PENDING_FIELD_INPUT, _(u"Pending Field Input")),
        (PASS_TO_ADMINISTRATOR,
            _(u"Pass To Administrator")),
        (RESET_TO_PREINTAKE, _(u"Reset To Preintake")),
        (RESET_TO_PREINTAKE_AND_SKIP_ALL_ZERO_VOTES_CHECK,
            _(u"Reset To Preintake And Skip All Zero Votes Check"))
    ]
