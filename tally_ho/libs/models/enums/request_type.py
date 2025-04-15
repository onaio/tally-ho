# -*- coding: utf-8 -*-
from django.utils.translation import gettext_lazy as _

from tally_ho.libs.utils.enum import Enum


class RequestType(Enum):
    RECALL_FROM_ARCHIVE = 0
    SEND_TO_CLEARANCE = 1

    CHOICES = [
        (RECALL_FROM_ARCHIVE, _('Recall from Archive')),
        (SEND_TO_CLEARANCE, _('Send to Clearance')),
    ]
