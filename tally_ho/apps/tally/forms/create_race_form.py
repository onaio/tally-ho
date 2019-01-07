from django import forms
from django.forms import ModelForm

from tally_ho.apps.tally.models.ballot import Ballot

disable_copy_input = {
    'onCopy': 'return false;',
    'onDrag': 'return false;',
    'onDrop': 'return false;',
    'onPaste': 'return false;',
    'autocomplete': 'off',
    'class': 'form-control'
}


class CreateRaceForm(ModelForm):
    class Meta:
        model = Ballot
        fields = localized_fields = [
            'number',
            'race_type',
            'active',
            'tally',
            'available_for_release',
        ]

        widgets = {"tally": forms.HiddenInput()}
