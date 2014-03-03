from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import ugettext as _
import reversion

from tally_system.apps.tally.models.result_form import ResultForm
from tally_system.libs.models.base_model import BaseModel


class QualityControl(BaseModel):
    class Meta:
        app_label = 'tally'

    result_form = models.ForeignKey(ResultForm)
    user = models.ForeignKey(User)

    active = models.BooleanField(default=True)
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
