from django import forms
from django.forms import ModelChoiceField, ModelForm
from tally_ho.apps.tally.forms.fields import RestrictedFileField

from tally_ho.apps.tally.models.ballot import Ballot
from tally_ho.apps.tally.models.electrol_race import ElectrolRace


class CreateBallotForm(ModelForm):
    class Meta:
        model = Ballot
        fields = localized_fields = [
            'number',
            'electrol_race',
            'active',
            'tally',
            'available_for_release',
            'document',
        ]

        widgets = {"tally": forms.HiddenInput()}
    document = RestrictedFileField(required=False)

    def __init__(self, *args, **kwargs):
        super(CreateBallotForm, self).__init__(*args, **kwargs)
        tally_id = self.initial.get('tally')
        self.fields['electrol_race'] = ModelChoiceField(
                queryset=ElectrolRace.objects.filter(tally__id=tally_id))
