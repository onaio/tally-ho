from django import forms
from django.utils.translation import gettext_lazy as _


class ConfirmResetForm(forms.Form):
    reject_reason = forms.CharField(
        required=True,
        label=_("Add comment(s) for rejecting this form"),
        widget=forms.Textarea(attrs={'cols': 80, 'rows': 5}),
    )
