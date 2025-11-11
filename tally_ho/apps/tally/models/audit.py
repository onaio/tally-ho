from django.db import models
from django.utils.translation import gettext_lazy as _
from enumfields import EnumIntegerField
import reversion

from tally_ho.apps.tally.models.quarantine_check import QuarantineCheck
from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.apps.tally.models.tally import Tally
from tally_ho.apps.tally.models.user_profile import UserProfile
from tally_ho.libs.models.base_model import BaseModel
from tally_ho.libs.models.enums.actions_prior import ActionsPrior
from tally_ho.libs.models.enums.audit_resolution import AuditResolution
from tally_ho.libs.utils.collections import keys_if_value


class Audit(BaseModel):
    class Meta:
        app_label = 'tally'

    quarantine_checks = models.ManyToManyField(QuarantineCheck)
    result_form = models.ForeignKey(ResultForm, on_delete=models.PROTECT)
    tally = models.ForeignKey(Tally,
                              on_delete=models.PROTECT,
                              related_name='audits')
    supervisor = models.ForeignKey(UserProfile,
                                   related_name='audit_user',
                                   null=True,
                                   on_delete=models.PROTECT)
    user = models.ForeignKey(UserProfile, on_delete=models.PROTECT)

    active = models.BooleanField(default=True)
    for_superadmin = models.BooleanField(default=False)
    reviewed_supervisor = models.BooleanField(default=False)
    reviewed_team = models.BooleanField(default=False)

    # Problem fields
    blank_reconciliation = models.BooleanField(default=False)
    blank_results = models.BooleanField(default=False)
    damaged_form = models.BooleanField(default=False)
    unclear_figures = models.BooleanField(default=False)
    other = models.TextField(null=True, blank=True)

    # Recommendations
    action_prior_to_recommendation = EnumIntegerField(ActionsPrior, blank=True,
                                                      null=True, default=4)
    resolution_recommendation = EnumIntegerField(
        AuditResolution, null=True, blank=True, default=0)

    # Comments
    team_comment = models.TextField(null=True, blank=True)
    supervisor_comment = models.TextField(null=True, blank=True)

    def get_problems(self):
        """Return a list of problems for this audit.

        Return a list of problems for which the problem checkbox has been
        selected.

        :returns: A list of strings.
        """
        problem_fields = {
            _('Blank Reconcilliation'): self.blank_reconciliation,
            _('Blank Results'): self.blank_results,
            _('Damaged Form'): self.damaged_form,
            _('Unclear Figures'): self.unclear_figures,
            _('Other'): self.other,
        }

        return keys_if_value(problem_fields)

    def action_prior_name(self):
        return _(self.action_prior_to_recommendation.label)

    def resolution_recommendation_name(self):
        return _(self.resolution_recommendation.label)

    def get_quarantine_check_details(self, check):
        """Get the details of a failed quarantine check
        including actual values.

        :param check: The QuarantineCheck instance
        :returns: A dictionary with check details and actual values
        """
        result_form = self.result_form
        recon_form = getattr(result_form, 'reconciliationform', None)

        if not recon_form:
            return None

        details = {
            'name': check.local_name(),
            'tolerance_value': check.value,
            'tolerance_percentage': check.percentage,
        }

        if check.method == 'pass_reconciliation_check':
            expected_total = (
                result_form.num_votes +
                recon_form.number_invalid_votes
            )
            actual_total = recon_form.number_sorted_and_counted
            allowed_tolerance = (
                check.value if check.value != 0
                else ((check.percentage / 100) * expected_total)
            )
            details.update({
                'expected_total': expected_total,
                'actual_total': actual_total,
                'allowed_tolerance': allowed_tolerance,
                'difference': abs(actual_total - expected_total),
                'num_votes': result_form.num_votes,
                'invalid_votes': recon_form.number_invalid_votes,
                'sorted_and_counted': recon_form.number_sorted_and_counted,
            })

        elif check.method == 'pass_over_voting_check':
            registrants = (
                result_form.station.registrants if result_form.station
                else None
            )
            if registrants is not None:
                allowed_tolerance = (
                    check.value if check.value != 0
                    else ((check.percentage / 100) * registrants)
                )
                total_votes = (
                    result_form.num_votes
                    + recon_form.number_invalid_votes
                )
                max_allowed = registrants + allowed_tolerance
                details.update({
                    'registrants': registrants,
                    'total_votes': total_votes,
                    'max_allowed': max_allowed,
                    'allowed_tolerance': allowed_tolerance,
                    'num_votes': result_form.num_votes,
                    'invalid_votes': recon_form.number_invalid_votes,
                })

        elif check.method == 'pass_card_check':
            voter_cards = recon_form.number_of_voter_cards_in_the_ballot_box
            allowed_tolerance = (
                check.value if check.value != 0
                else ((check.percentage / 100) * voter_cards)
            )
            total_ballot_papers = (
                recon_form.number_valid_votes + recon_form.number_invalid_votes
            )
            max_allowed = voter_cards + allowed_tolerance
            details.update({
                'voter_cards': voter_cards,
                'total_ballot_papers': total_ballot_papers,
                'max_allowed': max_allowed,
                'allowed_tolerance': allowed_tolerance,
                'valid_votes': recon_form.number_valid_votes,
                'invalid_votes': recon_form.number_invalid_votes,
            })

        return details

    def save(self, *args, **kwargs):
        if not self.tally_id and self.result_form_id:
            self.tally_id = self.result_form.tally_id
        super().save(*args, **kwargs)


reversion.register(Audit)
