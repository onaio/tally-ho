from django.contrib.auth.models import User
from django.db import models
from django_enumfield import enum
import reversion

from libya_tally.apps.tally.models.candidate import Candidate
from libya_tally.apps.tally.models.result_form import ResultForm
from libya_tally.libs.models.base_model import BaseModel
from libya_tally.libs.models.enums.entry_version import EntryVersion


class Result(BaseModel):
    class Meta:
        app_label = 'tally'

    candidate = models.ForeignKey(Candidate, related_name='results')
    result_form = models.ForeignKey(ResultForm, related_name='results')
    user = models.ForeignKey(User, null=True)

    active = models.BooleanField(default=True)
    entry_version = enum.EnumField(EntryVersion)
    votes = models.PositiveIntegerField()


reversion.register(Result)
