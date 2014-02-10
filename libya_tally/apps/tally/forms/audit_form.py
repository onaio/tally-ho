from django.forms import ModelForm

from libya_tally.apps.tally.models.audit import Audit


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
            'audit_review_team_comments',
            'supervisor_comment']
