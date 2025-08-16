from django.db import models
from django.utils.translation import gettext_lazy as _
import reversion

from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.apps.tally.models.tally import Tally
from tally_ho.apps.tally.models.user_profile import UserProfile
from tally_ho.libs.models.base_model import BaseModel


class QualityControl(BaseModel):
    class Meta:
        app_label = 'tally'

    result_form = models.ForeignKey(ResultForm, on_delete=models.PROTECT)
    tally = models.ForeignKey(Tally,
                              on_delete=models.PROTECT,
                              default=1,
                              related_name='quality_controls')
    user = models.ForeignKey(UserProfile, on_delete=models.PROTECT)

    active = models.BooleanField(default=True)
    passed_qc = models.BooleanField(null=True)
    passed_presidential = models.BooleanField(null=True)
    passed_general = models.BooleanField(null=True)
    passed_reconciliation = models.BooleanField(null=True)
    passed_women = models.BooleanField(null=True)

    @property
    def reviews_passed(self):
        """Return True if this quality control has passed, otherwise False.

        :returns: True if this quality control has passed, otherwise False.
        """
        rf = self.result_form

        return (
            (not rf.has_results or self.passed_qc) and
            (not rf.reconciliationform or self.passed_reconciliation))

    @property
    def reviews_required_text(self):
        return _('Reviews Completed') if self.reviews_passed else\
            _('Reviews Required')

    def save(self, *args, **kwargs):
        if not self.tally_id and self.result_form_id:
            self.tally_id = self.result_form.tally_id
        super().save(*args, **kwargs)


reversion.register(QualityControl)
