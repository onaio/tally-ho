from django.db import models
from django_enumfield import enum

from libya_tally.libs.models.base_model import BaseModel
from libya_tally.libs.models.enums.entry_version import EntryVersion


class Result(BaseModel):
    class Meta:
        app_label = 'tally'

    candidate = models.ForeignKey('Candidate', related_name='candidates')
    result_form = models.ForeignKey('ResultForm', related_name='results')

    entry_version = enum.EnumField(EntryVersion)
