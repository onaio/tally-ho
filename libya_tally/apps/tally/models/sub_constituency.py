from django.db import models
from django.utils.translation import ugettext as _

from libya_tally.apps.tally.models.ballot import Ballot
from libya_tally.libs.models.base_model import BaseModel


class SubConstituency(BaseModel):
    class Meta:
        app_label = 'tally'

    ballot_general = models.ForeignKey(Ballot, null=True,
                                       related_name='sc_general')
    ballot_women = models.ForeignKey(Ballot, null=True,
                                     related_name='sc_women')
    code = models.PositiveSmallIntegerField()  # aka SubCon number
    component_ballot = models.BooleanField()
    field_office = models.CharField(max_length=256)
    number_of_ballots = models.PositiveSmallIntegerField(null=True)
    races = models.PositiveSmallIntegerField(null=True)

    @property
    def form_type(self):
        ballot = self.ballot

        if ballot.ballot_women.first():
            return _('General and Women')
        elif ballot.ballot_general.first():
            if ballot.ballot_general.first().component_ballot:
                return _('General and Component')

            return _('General')
        else:
            return _('Undefined')
