from django_enumfield import enum
from django.utils.translation import ugettext_lazy as _


class AuditResolution(enum.Enum):
    EMPTY = 0
    NO_PROBLEM_TO_DE_1 = 1
    CLARIFIED_FIGURES_TO_DE_1 = 2
    OTHER_CORRECTION_TO_DE_1 = 3
    MAKE_AVAILABLE_FOR_ARCHIVE = 4


AUDIT_CHOICES = [
    (AuditResolution.EMPTY, '----'),
    (AuditResolution.NO_PROBLEM_TO_DE_1, _(u"No Problem To Data Entry 1")),
    (AuditResolution.CLARIFIED_FIGURES_TO_DE_1,
     _(u"Clarified Figures To Data Entry 1")),
    (AuditResolution.OTHER_CORRECTION_TO_DE_1,
     _(u"Other Correction To Data Entry 1")),
    (AuditResolution.MAKE_AVAILABLE_FOR_ARCHIVE,
     _(u"Make Available For Archive"))
]
