from django import forms

from tally_ho.apps.tally.models.audit import Audit
from tally_ho.libs.models.enums import actions_prior
from tally_ho.libs.models.enums import audit_resolution


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
        required=False, choices=actions_prior.ACTION_CHOICES,
        coerce=int)
    resolution_recommendation = forms.TypedChoiceField(
        required=False, choices=audit_resolution.AUDIT_CHOICES,
        coerce=int)
