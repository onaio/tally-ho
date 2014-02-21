from django import forms

from libya_tally.apps.tally.models.clearance import Clearance
from libya_tally.libs.models.enums import actions_prior
from libya_tally.libs.models.enums import clearance_resolution


EMPTY_KEY = 0


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
        required=False, choices=actions_prior.ACTION_CHOICES, coerce=int)
    resolution_recommendation = forms.TypedChoiceField(
        required=False, choices=clearance_resolution.CLEARANCE_CHOICES,
        coerce=int)

    def clean(self):
        cleaned_data = super(ClearanceForm, self).clean()
        action = cleaned_data.get('action_prior_to_recommendation')
        resolution = cleaned_data.get('resolution_recommendation')

        if action == EMPTY_KEY:
            cleaned_data['action_prior_to_recommendation'] = None

        if resolution == EMPTY_KEY:
            cleaned_data['resolution_recommendation'] = None

        return cleaned_data
