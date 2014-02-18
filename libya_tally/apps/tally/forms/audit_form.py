from django.forms import ModelForm, TypedChoiceField

from libya_tally.apps.tally.models.audit import Audit
from libya_tally.libs.models.enums.actions_prior import ActionsPrior
from libya_tally.libs.models.enums.audit_resolution import AuditResolution


class AuditForm(ModelForm):
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

    # Recommendations
    action_prior_to_recommendation = TypedChoiceField(
        required=False, choices=[('', '----')] + ActionsPrior.choices(),
        coerce=int)
    resolution_recommendation = TypedChoiceField(
        required=False, choices=[('', '----')] + AuditResolution.choices(),
        coerce=int)

    def clean(self):
        cleaned_data = super(AuditForm, self).clean()
        action = cleaned_data.get('action_prior_to_recommendation')
        resolution = cleaned_data.get('resolution_recommendation')

        if action == '':
            cleaned_data['action_prior_to_recommendation'] = None

        if resolution == '':
            cleaned_data['resolution_recommendation'] = None

        return cleaned_data
