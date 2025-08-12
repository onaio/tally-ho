from django.utils.translation import gettext_lazy as _

from tally_ho.libs.utils.enum import Enum


class RequestStatus(Enum):
    PENDING = 0
    APPROVED = 1
    REJECTED = 2

    CHOICES = [
        (PENDING, _('Pending Approval')),
        (APPROVED, _('Approved')),
        (REJECTED, _('Rejected')),
    ]
