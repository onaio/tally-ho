from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import ugettext as _

from libya_tally.apps.tally.models.result_form import ResultForm
from libya_tally.libs.models.base_model import BaseModel


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
        result_form = self.result_form
        has_recon_form = True

        try:
            result_form.reconciliationform
        except Exception:
            has_recon_form = False

        return (
            (not result_form.has_general_results or self.passed_general) and
            (not has_recon_form or self.passed_reconciliation) and
            (not result_form.has_women_results or self.passed_women))

    @property
    def reviews_required_text(self):
        return _('Reviews Completed') if self.reviews_passed else\
            _('Reviews Required')
