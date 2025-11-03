from django import forms
from django.utils.translation import gettext_lazy as _


class ConfirmResetForm(forms.Form):
    reason = forms.CharField(
        required=True,
        label=_("Reason for resetting this form"),
        widget=forms.Textarea(attrs={'cols': 80, 'rows': 5}),
    )
