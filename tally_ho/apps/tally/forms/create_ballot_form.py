from django import forms
from django.forms import ModelForm
from tally_ho.apps.tally.forms.fields import RestrictedFileField

from tally_ho.apps.tally.models.ballot import Ballot


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
