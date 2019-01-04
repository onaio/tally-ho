from django import forms
from django.forms import ModelForm
from tally_ho.apps.tally.models.station import Station

disable_copy_input = {
    'onCopy': 'return false;',
    'onDrag': 'return false;',
    'onDrop': 'return false;',
    'onPaste': 'return false;',
    'autocomplete': 'off',
    'class': 'form-control'
}


class CreateStationForm(ModelForm):
    class Meta:
        model = Station
        fields = localized_fields = [
            'center',
            'station_number',
            'gender',
            'sub_constituency',
            'tally',
            'registrants',
        ]

        widgets = {
            "tally": forms.HiddenInput()
        }
