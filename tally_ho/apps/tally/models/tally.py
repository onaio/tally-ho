from django.db import models
from enumfields import EnumIntegerField

from tally_ho.libs.models.base_model import BaseModel
from tally_ho.libs.models.enums.disable_reason import DisableReason
from tally_ho.libs.utils.templates import (
    get_tally_administer_link,
    get_tally_edit_link,
)


class Tally(BaseModel):
    class Meta:
        app_label = 'tally'

    name = models.CharField(
        max_length=255, null=False, blank=False, unique=True)
    active = models.BooleanField(default=True)
    disable_reason = EnumIntegerField(DisableReason, null=True)
    print_cover_in_intake = models.BooleanField(default=True,
        help_text='Enable/disable cover printing in Intake stage')
    print_cover_in_clearance = models.BooleanField(default=True,
        help_text='Enable/disable cover printing in Clearance stage')
    print_cover_in_quality_control = models.BooleanField(default=True,
        help_text='Enable/disable cover printing in Quality Control stage')
    print_cover_in_audit = models.BooleanField(default=True,
        help_text='Enable/disable cover printing in Audit stage')

    def __str__(self):
        return u'%d - %s' % (self.id, self.name)

    @property
    def administer_button(self):
        return get_tally_administer_link(self)

    @property
    def edit_button(self):
        return get_tally_edit_link(self)
