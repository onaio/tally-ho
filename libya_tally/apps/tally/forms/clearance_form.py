from django.forms import ModelForm

from libya_tally.apps.tally.models.clearance import Clearance


class ClearanceForm(ModelForm):
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
            'audit_review_team_comments',
            'supervisor_comment']
