from django import forms
from django.utils.translation import ugettext as _


disable_copy_input = {
    'onCopy': 'return false;',
    'onDrag': 'return false;',
    'onDrop': 'return false;',
    'onPaste': 'return false;',
    'autocomplete': 'off',
    'class': 'form-control required'
}


class CandidateForm(forms.Form):
    votes = forms.IntegerField(min_value=0, required=True,
                               widget=forms.TextInput(
                                   attrs=disable_copy_input),
                               label=_(u"Votes"))
