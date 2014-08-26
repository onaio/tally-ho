from django.db import models
from django.utils.translation import ugettext as _
from django_enumfield import enum
import reversion

from tally_ho.apps.tally.models.tally import Tally
from tally_ho.apps.tally.models.office import Office
from tally_ho.apps.tally.models.sub_constituency import SubConstituency
from tally_ho.libs.models.base_model import BaseModel
from tally_ho.libs.models.dependencies import check_results_for_forms
from tally_ho.libs.models.enums.center_type import CenterType
from tally_ho.libs.models.enums.disable_reason import DisableReason


class Center(BaseModel):
    class Meta:
        app_label = 'tally'
        ordering = ['code']
        unique_together = ('code', 'tally')

    sub_constituency = models.ForeignKey(SubConstituency,
                                         related_name='centers', null=True)

    center_type = enum.EnumField(CenterType)
    code = models.PositiveIntegerField()  # a.k.a. Center Number
    latitude = models.FloatField(null=True)
    longitude = models.FloatField(null=True)
    mahalla = models.TextField()
    name = models.TextField()
    office = models.ForeignKey(Office, null=True)
    region = models.TextField()
    village = models.TextField()
    active = models.BooleanField(default=True)
    disable_reason = enum.EnumField(DisableReason, null=True)
    tally = models.ForeignKey(Tally, null=True, blank=True, related_name='centers')

    def remove(self):
        """Remove this center and related information.

        Stop and do nothing if there are results for this center.  Removes the
        result forms and stations associated with this center.

        :raises: `Exception` if any results exist in any result forms are
            associated with this center.
        """
        resultforms = self.resultform_set.all()

        check_results_for_forms(resultforms)
        resultforms.delete()
        self.stations.all().delete()

        self.delete()

    def sc_code(self):
        return self.sub_constituency.code if self.sub_constituency else _(
            'Special')

    def __unicode__(self):
        return u'%s - %s' % (self.code, self.name)

    @property
    def status(self):
        return 'Enabled' if self.active else 'Disabled'

    @property
    def center_type_name(self):
        return 'Special' if self.center_type == 1 else 'General'

reversion.register(Center)
