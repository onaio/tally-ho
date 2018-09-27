from django.utils.translation import ugettext_lazy as _

from tally_ho.libs.utils.enum import Enum


class DisableReason(Enum):
    NOT_OPENED = 0
    HNEC_DECISION = 1
    DISQUALIFIED = 2
    MATERIALS_DESTROYED = 3
    OTHER = 4

    CHOICES = [
        (NOT_OPENED, _('Not opened')),
        (HNEC_DECISION, _('HNEC decision on irregularities')),
        (DISQUALIFIED, _('Disqualified due to court decision')),
        (MATERIALS_DESTROYED, _('Materials destroyed')),
        (OTHER, _('Other'))
    ]
