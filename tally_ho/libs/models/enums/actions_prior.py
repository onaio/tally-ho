from enum import Enum
from django.utils.translation import ugettext_lazy as _


class ActionsPrior(Enum):
    REQUEST_COPY_FROM_FIELD = 0
    REQUEST_AUDIT_ACTION_FROM_FIELD = 1
    PENDING_ADVICE = 2
    NONE_REQUIRED = 3
    EMPTY = 4


ACTION_CHOICES = [
    (ActionsPrior.EMPTY, '----'),
    (ActionsPrior.REQUEST_COPY_FROM_FIELD, _(u"Request Copy From Field")),
    (ActionsPrior.REQUEST_AUDIT_ACTION_FROM_FIELD,
     _(u"Request Audit Action From Field")),
    (ActionsPrior.PENDING_ADVICE, _(u"Pending Advice")),
    (ActionsPrior.NONE_REQUIRED, _(u"None Required"))
]
