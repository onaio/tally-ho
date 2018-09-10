from django import forms

from tally_ho.apps.tally.models.audit import Audit
from tally_ho.libs.models.enums.actions_prior import ActionsPrior
from tally_ho.libs.models.enums.audit_resolution import AuditResolution


class AuditForm(forms.ModelForm):
    class Meta:
        model = Audit
        fields = [
            'blank_reconciliation',
            'blank_results',
            'damaged_form',
            'unclear_figures',
            'other',
            # Recommendations
            'action_prior_to_recommendation',
            'resolution_recommendation',
            # Comments
            'team_comment',
            'supervisor_comment']

    other = forms.CharField(required=False)
    action_prior_to_recommendation = forms.TypedChoiceField(
        required=False, choices=ActionsPrior.choices(),
        coerce=int)
    resolution_recommendation = forms.TypedChoiceField(
        required=False, choices=AuditResolution.choices(),
        coerce=int)
