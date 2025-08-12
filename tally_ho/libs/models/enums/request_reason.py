from django.utils.translation import gettext_lazy as _

from tally_ho.libs.utils.enum import Enum


class RequestReason(Enum):
    INCORRECT_ARCHIVE = 0
    DATA_ENTRY_ERROR = 1
    CLEARANCE_NEEDED = 2
    OTHER = 3

    CHOICES = [
        (INCORRECT_ARCHIVE, _('Incorrectly Archived')),
        (DATA_ENTRY_ERROR, _('Data Entry Error Correction')),
        (CLEARANCE_NEEDED, _('Clearance Required')),
        (OTHER, _('Other (Specify in Comment)')),
    ]
