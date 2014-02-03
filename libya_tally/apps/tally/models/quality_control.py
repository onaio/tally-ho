from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import ugettext as _

from libya_tally.apps.tally.models.result_form import ResultForm
from libya_tally.libs.models.base_model import BaseModel


class QualityControl(BaseModel):
    class Meta:
        app_label = 'tally'

    result_form = models.OneToOneField(ResultForm)
    user = models.ForeignKey(User)

    passed_general = models.NullBooleanField()
    passed_reconciliation = models.NullBooleanField()
    passed_womens = models.NullBooleanField()

    def reviews_complete(self):
        return self.passed_general and self.passed_reconciliation and\
            self.passed_womens

    def reviews_required_text(self):
        return _('Reviews Completed') if self.reviews_complete() else\
            _('Reviews Required')
