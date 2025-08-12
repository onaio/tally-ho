from django.utils.translation import gettext_lazy as _

from tally_ho.libs.utils.enum import Enum


class ActionsPrior(Enum):
    REQUEST_COPY_FROM_FIELD = 0
    REQUEST_AUDIT_ACTION_FROM_FIELD = 1
    PENDING_ADVICE = 2
    NONE_REQUIRED = 3
    EMPTY = 4

    CHOICES = [
        (EMPTY, '----'),
        (REQUEST_COPY_FROM_FIELD, _("Request Copy From Field")),
        (REQUEST_AUDIT_ACTION_FROM_FIELD,
         _("Request Audit Action From Field")),
        (PENDING_ADVICE, _("Pending Advice")),
        (NONE_REQUIRED, _("None Required"))
    ]
