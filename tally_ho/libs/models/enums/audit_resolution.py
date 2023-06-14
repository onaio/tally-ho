from django.utils.translation import gettext_lazy as _

from tally_ho.libs.utils.enum import Enum


class AuditResolution(Enum):
    EMPTY = 0
    NO_PROBLEM_TO_DE_1 = 1
    CLARIFIED_FIGURES_TO_DE_1 = 2
    OTHER_CORRECTION_TO_DE_1 = 3
    MAKE_AVAILABLE_FOR_ARCHIVE = 4

    CHOICES = [
        (EMPTY, '----'),
        (NO_PROBLEM_TO_DE_1, _(u"No Problem To Data Entry 1")),
        (CLARIFIED_FIGURES_TO_DE_1,
         _(u"Clarified Figures To Data Entry 1")),
        (OTHER_CORRECTION_TO_DE_1,
         _(u"Other Correction To Data Entry 1")),
        (MAKE_AVAILABLE_FOR_ARCHIVE,
         _(u"Make Available For Archive"))
    ]
