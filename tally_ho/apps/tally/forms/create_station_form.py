from django import forms

from django.forms import (
    ModelForm,
    ModelChoiceField,
    TypedChoiceField,
)
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


def append_default_empty_option(choices):
    """Add default empty option to Gender choices.

    :param choices: List of Gender choices
    :returns: A list Gender choices.
    """
    gender_choices = deque(choices)
    gender_choices.appendleft(tuple(['', 'Select Gender']))

    return list(gender_choices)


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
