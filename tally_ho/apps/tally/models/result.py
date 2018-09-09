from django.contrib.auth.models import User
from django.db import models
from enumfields import EnumField
import reversion

from tally_ho.apps.tally.models.candidate import Candidate
from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.libs.models.base_model import BaseModel
from tally_ho.libs.models.enums.entry_version import EntryVersion


class Result(BaseModel):
    class Meta:
        app_label = 'tally'

    candidate = models.ForeignKey(Candidate,
                                  related_name='results',
                                  on_delete=models.PROTECT)
    result_form = models.ForeignKey(ResultForm,
                                    related_name='results',
                                    on_delete=models.PROTECT)
    user = models.ForeignKey(User,
                             null=True,
                             on_delete=models.PROTECT)

    active = models.BooleanField(default=True)
    entry_version = EnumField(EntryVersion)
    votes = models.PositiveIntegerField()


reversion.register(Result)
