from django_enumfield import enum
from django.utils.translation import ugettext_lazy as _


class DisableReason(enum.Enum):
    NOT_OPENED = 0
    HNEC_DECISION = 1
    DISQUALIFIED = 2
    MATERIALS_DESTROYED = 3
    OTHER = 4

    text_equivalents = {NOT_OPENED: _('Not opened'),
                        HNEC_DECISION: _('HNEC decision on irregularities'),
                        DISQUALIFIED: _('Disqualified due to court decision'),
                        MATERIALS_DESTROYED: _('Materials destroyed'),
                        OTHER: _('Other')}
