import reversion
from django.db import models
from django.utils.translation import gettext_lazy as _
from enumfields import EnumIntegerField

from tally_ho.apps.tally.models.constituency import Constituency
from tally_ho.apps.tally.models.office import Office
from tally_ho.apps.tally.models.sub_constituency import SubConstituency
from tally_ho.apps.tally.models.tally import Tally
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
                                         on_delete=models.PROTECT,
                                         related_name='centers', null=True)

    center_type = EnumIntegerField(CenterType, blank=True, null=True)
    code = models.PositiveIntegerField()  # a.k.a. Center Number
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    mahalla = models.TextField(blank=True, null=True)
    name = models.TextField()
    office = models.ForeignKey(Office, on_delete=models.PROTECT, null=True)
    region = models.TextField(blank=True, null=True)
    village = models.TextField(blank=True, null=True)
    active = models.BooleanField(default=True)
    disable_reason = EnumIntegerField(DisableReason, null=True)
    tally = models.ForeignKey(Tally,
                              null=True,
                              blank=True,
                              related_name='centers',
                              on_delete=models.PROTECT)
    constituency = models.ForeignKey(Constituency,
                                     null=True,
                                     blank=True,
                                     related_name='centers',
                                     on_delete=models.PROTECT)

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

    def __str__(self):
        return '%s - %s' % (self.code, self.name)

    @property
    def status(self):
        return 'Enabled' if self.active else 'Disabled'

    @property
    def center_type_name(self):
        return 'Special' if self.center_type == 1 else 'General'


reversion.register(Center)
