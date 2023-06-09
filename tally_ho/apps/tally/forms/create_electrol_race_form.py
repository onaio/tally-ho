from django import forms
from django.forms import ModelForm

from tally_ho.apps.tally.models.electrol_race import ElectrolRace


class CreateElectrolRaceForm(ModelForm):
    class Meta:
        model = ElectrolRace
        fields = localized_fields = [
            'election_level',
            'ballot_name',
            'active',
            'tally',
        ]

        widgets = {"tally": forms.HiddenInput()}
