from django.utils.translation import gettext_lazy as _

from tally_ho.libs.utils.enum import Enum


class DisableReason(Enum):
    NOT_OPENED = 0
    HNEC_DECISION = 1
    COMPLAINT_COURT = 2
    COMPLAINT_HNEC = 3
    DISQUALIFIED_HNEC = 4
    DISQUALIFIED_COURT = 5
    MATERIALS_DESTROYED = 6
    OTHER = 7

    CHOICES = [
        (NOT_OPENED, _('Not opened')),
        (HNEC_DECISION, _('HNEC decision on irregularities')),
        (COMPLAINT_HNEC, _('Subject to on-going complaint to HNEC')),
        (COMPLAINT_COURT, _('Subject to on-going complaint to Courts')),
        (DISQUALIFIED_HNEC, _('Disqualified due to HNEC decision')),
        (DISQUALIFIED_COURT, _('Disqualified due to court decision')),
        (MATERIALS_DESTROYED, _('Materials destroyed')),
        (OTHER, _('Other'))
    ]
