from django.utils.translation import gettext_lazy as _

from tally_ho.libs.utils.enum import Enum


class AuditResolution(Enum):
    EMPTY = 0
    NO_PROBLEM_TO_DE_1 = 1
    CLARIFIED_FIGURES_TO_DE_1 = 2
    OTHER_CORRECTION_TO_DE_1 = 3
    MAKE_AVAILABLE_FOR_ARCHIVE = 4
    SEND_TO_CLEARANCE = 5

    CHOICES = [
        (EMPTY, '----'),
        (NO_PROBLEM_TO_DE_1, _("No Problem To Data Entry 1")),
        (CLARIFIED_FIGURES_TO_DE_1,
         _("Clarified Figures To Data Entry 1")),
        (OTHER_CORRECTION_TO_DE_1,
         _("Other Correction To Data Entry 1")),
        (MAKE_AVAILABLE_FOR_ARCHIVE,
         _("Make Available For Archive")),
        (SEND_TO_CLEARANCE, _("Send to Clearance"))
    ]
