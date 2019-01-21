from django import forms
from django.forms import ModelForm
from .fields import RestrictedFileField

from tally_ho.apps.tally.models.ballot import Ballot


class CreateRaceForm(ModelForm):
    class Meta:
        model = Ballot
        fields = localized_fields = [
            'number',
            'race_type',
            'active',
            'tally',
            'available_for_release',
            'document',
        ]

        widgets = {"tally": forms.HiddenInput()}
    document = RestrictedFileField(
            allowed_extensions=['png', 'jpg', 'doc', 'pdf']
        )
