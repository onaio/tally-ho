from django import forms
from django.utils.translation import gettext_lazy as _

from tally_ho.apps.tally.models import WorkflowRequest


class RequestRecallForm(forms.ModelForm):
    class Meta:
        model = WorkflowRequest
        fields = ['request_reason', 'request_comment']
        widgets = {
            'request_reason': forms.Select(attrs={'class': 'form-control'}),
            'request_comment': forms.Textarea(
                attrs={'rows': 3, 'class': 'form-control'}),
        }
        labels = {
            'request_reason': _("Reason for Recall"),
            'request_comment': _("Comment (Required)"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['request_comment'].required = True


class ApprovalForm(forms.ModelForm):
    class Meta:
        model = WorkflowRequest
        fields = ['approval_comment']
        widgets = {
            'approval_comment': forms.Textarea(
                attrs={'rows': 3, 'class': 'form-control'}),
        }
        labels = {
            'approval_comment': _("Approval/Rejection Comment"),
        }
