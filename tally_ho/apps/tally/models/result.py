from django.contrib.auth.models import User
from django.db import models
from django_enumfield import enum
import reversion

from tally_ho.apps.tally.models.candidate import Candidate
from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.libs.models.base_model import BaseModel
from tally_ho.libs.models.enums.entry_version import EntryVersion


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
