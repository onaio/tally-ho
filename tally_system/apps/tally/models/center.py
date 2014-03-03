from django.db import models
from django.utils.translation import ugettext as _
from django_enumfield import enum
import reversion

from tally_system.apps.tally.models.office import Office
from tally_system.apps.tally.models.sub_constituency import SubConstituency
from tally_system.libs.models.base_model import BaseModel
from tally_system.libs.models.dependencies import check_results_for_forms
from tally_system.libs.models.enums.center_type import CenterType


class Center(BaseModel):
    class Meta:
        app_label = 'tally'
        ordering = ['code']

    sub_constituency = models.ForeignKey(SubConstituency,
                                         related_name='centers', null=True)

    center_type = enum.EnumField(CenterType)
    code = models.PositiveIntegerField(unique=True)  # a.k.a. Center Number
    latitude = models.FloatField(null=True)
    longitude = models.FloatField(null=True)
    mahalla = models.TextField()
    name = models.TextField()
    office = models.ForeignKey(Office, null=True)
    region = models.TextField()
    village = models.TextField()

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


reversion.register(Center)
