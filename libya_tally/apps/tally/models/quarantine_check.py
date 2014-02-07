from django.contrib.auth.models import User
from django.db import models

from libya_tally.apps.tally.models.reconciliation_form import\
    ReconciliationForm
from libya_tally.libs.models.base_model import BaseModel


class QuarantineCheck(BaseModel):
    class Meta:
        app_label = 'tally'

    user = models.ForeignKey(User)

    name = models.CharField(max_length=256)
    rule = models.CharField(max_length=256)
    value = models.FloatField()

    def pass_overvote(self, result_form):
        """Check to guard against overvoting.

        If the `result_form` does not have a `reconciliation_form` this will
        always return True.

        Fails if the number of ballots reported to be used in a station exceeds
        the number of potential voters minus the number of registrants plus N
        persons to accomodate staff and security.

        :param result_form: The result form to check.
        :returns: A boolean of true if passed, otherwise false.
        """
        try:
            recon_form = result_form.reconciliation_form
        except ReconciliationForm.DoesNotExists:
            return True

        recon_form.number_ballots_used
