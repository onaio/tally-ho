from django import forms
from django.db import models

from django.forms import (
    ModelForm,
    ModelChoiceField,
    ValidationError
)
from django.utils.translation import ugettext as _
from tally_ho.apps.tally.models.station import Station
from tally_ho.apps.tally.models.center import Center
from tally_ho.apps.tally.models.sub_constituency import SubConstituency
from tally_ho.libs.models.enums.gender import Gender

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

    def __init__(self, *args, **kwargs):
        super(CreateStationForm, self).__init__(*args, **kwargs)

        if self.initial.get('tally'):
            self.fields['center'] = ModelChoiceField(
                queryset=Center.objects.filter(
                    tally__id=self.initial['tally']))
            self.fields['sub_constituency'] = ModelChoiceField(
                queryset=SubConstituency.objects.filter(
                    tally__id=self.initial['tally']))

        self.fields['gender'].choices = self.fields['gender'].choices[:-1]

    def clean(self):
        cleaned_data = super(CreateStationForm, self).clean()

        center = cleaned_data.get('center')
        if not center:
            raise ValidationError(_('Center field is required'))

        return cleaned_data
