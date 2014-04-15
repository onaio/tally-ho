from django.db import models
from django.utils.translation import ugettext as _
import reversion

from tally_ho.apps.tally.models.ballot import Ballot
from tally_ho.libs.models.base_model import BaseModel


class SubConstituency(BaseModel):
    class Meta:
        app_label = 'tally'

    ballot_component = models.ForeignKey(Ballot, null=True,
                                         related_name='sc_component')
    ballot_general = models.ForeignKey(Ballot, null=True,
                                       related_name='sc_general')
    ballot_women = models.ForeignKey(Ballot, null=True,
                                     related_name='sc_women')
    code = models.PositiveSmallIntegerField()  # aka SubCon number
    field_office = models.CharField(max_length=256)
    number_of_ballots = models.PositiveSmallIntegerField(null=True)
    races = models.PositiveSmallIntegerField(null=True)

    @property
    def form_type(self):
        """Return the form type of ballots used in this subconstituency.

        :returns: The type of ballot that is used in this subconstituency.
        """
        if self.ballot_women:
            return _('Women')
        elif self.ballot_general:
            if self.ballot_component:
                return _('General and Component')

            return _('General')
        else:
            return _('Undefined')


reversion.register(SubConstituency)
