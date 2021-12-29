from django.db import models
from django.utils.translation import ugettext as _
import reversion

from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.apps.tally.models.user_profile import UserProfile
from tally_ho.libs.models.base_model import BaseModel


class QualityControl(BaseModel):
    class Meta:
        app_label = 'tally'

    result_form = models.ForeignKey(ResultForm, on_delete=models.PROTECT)
    user = models.ForeignKey(UserProfile, on_delete=models.PROTECT)

    active = models.BooleanField(default=True)
    passed_presidential = models.NullBooleanField()
    passed_general = models.NullBooleanField()
    passed_reconciliation = models.NullBooleanField()
    passed_women = models.NullBooleanField()

    @property
    def reviews_passed(self):
        """Return True if this quality control has passed, otherwise False.

        :returns: True if this quality control has passed, otherwise False.
        """
        rf = self.result_form

        return (
            (not rf.has_general_results or self.passed_general) and
            (not rf.reconciliationform or self.passed_reconciliation) and
            (not rf.has_women_results or self.passed_women))

    @property
    def reviews_required_text(self):
        return _('Reviews Completed') if self.reviews_passed else\
            _('Reviews Required')


reversion.register(QualityControl)
