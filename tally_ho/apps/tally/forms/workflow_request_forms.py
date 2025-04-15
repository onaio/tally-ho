# -*- coding: utf-8 -*-
from django import forms
from django.utils.translation import gettext_lazy as _

from tally_ho.apps.tally.models import WorkflowRequest
from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.libs.models.enums.form_state import FormState
from tally_ho.libs.models.enums.request_reason import RequestReason
from tally_ho.libs.models.enums.request_status import RequestStatus
from tally_ho.libs.models.enums.request_type import RequestType


class InitiateRecallBarcodeForm(forms.ModelForm):
    class Meta:
        model = WorkflowRequest
        fields = ['request_type', 'request_reason', 'request_comment']

    barcode = forms.CharField(
        label=_("Archived Form Barcode"),
        widget=forms.TextInput(attrs={'autofocus': 'autofocus',
                                     'class': 'form-control'}),
        max_length=255)
    tally_id = forms.IntegerField(widget=forms.HiddenInput())

    def clean(self):
        cleaned_data = super().clean()
        barcode = cleaned_data.get("barcode")
        tally_id = cleaned_data.get("tally_id")

        if barcode and tally_id:
            try:
                result_form = ResultForm.objects.get(
                    barcode=barcode, tally__id=tally_id)

                if result_form.form_state != FormState.ARCHIVED:
                    raise forms.ValidationError(
                        _("This form is not in the ARCHIVED state."))

                # Check if there is already an active PENDING recall request
                if WorkflowRequest.objects.filter(
                    result_form=result_form,
                    request_type=RequestType.RECALL_FROM_ARCHIVE,
                    status=RequestStatus.PENDING).exists():
                    raise forms.ValidationError(
                        _(str("An active recall request already"
                              " exists for this form.")))

                cleaned_data['result_form'] = result_form
            except ResultForm.DoesNotExist:
                raise forms.ValidationError(
                    _("No result form found with this barcode in this tally."))

        return cleaned_data


class RequestRecallForm(forms.ModelForm):
    class Meta:
        model = WorkflowRequest
        fields = ['request_reason', 'request_comment']
        widgets = {
            'request_reason': forms.Select(attrs={'class': 'form-control'}),
            'request_comment': forms.Textarea(
                attrs={'rows': 3, 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['request_reason'].choices = RequestReason.CHOICES
        self.fields['request_comment'].required = True


class ApprovalForm(forms.ModelForm):
    class Meta:
        model = WorkflowRequest
        fields = ['approval_comment']

    approval_comment = forms.CharField(
        label=_("Approval/Rejection Comment"),
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        required=False)
