from django.db import models
from enumfields import EnumIntegerField
import reversion

from tally_ho.apps.tally.models.candidate import Candidate
from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.apps.tally.models.user_profile import UserProfile
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
    user = models.ForeignKey(UserProfile,
                             null=True,
                             on_delete=models.PROTECT)

    active = models.BooleanField(default=True)
    entry_version = EnumIntegerField(EntryVersion)
    votes = models.PositiveIntegerField()


reversion.register(Result)
