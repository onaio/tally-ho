from django.db import models

from libya_tally.libs.models.base_model import BaseModel
from tally.libs.models.enums.entry_version import EntryVersion


class Result(BaseModel):
    candidate = models.ForeignKey('Candidate')
    result_form = models.ForeignKey('ResultForm')

    entry_version = models.EnumField(EntryVersion)
