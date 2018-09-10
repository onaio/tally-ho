from django import forms

from tally_ho.apps.tally.models.clearance import Clearance
from tally_ho.libs.models.enums.actions_prior import ActionsPrior
from tally_ho.libs.models.enums.clearance_resolution import ClearanceResolution


class ClearanceForm(forms.ModelForm):
    class Meta:
        model = Clearance
        fields = [
            'center_name_missing',
            'center_name_mismatching',
            'center_code_missing',
            'center_code_mismatching',
            'form_already_in_system',
            'form_incorrectly_entered_into_system',
            'other',
            # Recommendations
            'action_prior_to_recommendation',
            'resolution_recommendation',
            # Comments
            'team_comment',
            'supervisor_comment']

    other = forms.CharField(required=False)
    action_prior_to_recommendation = forms.TypedChoiceField(
        required=False, choices=ActionsPrior.choices(), coerce=int)
    resolution_recommendation = forms.TypedChoiceField(
        required=False, choices=ClearanceResolution.choices(),
        coerce=int)
