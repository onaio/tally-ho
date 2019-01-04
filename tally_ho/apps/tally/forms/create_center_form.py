from django import forms
from django.forms import ModelForm, Textarea
from tally_ho.apps.tally.models.center import Center

disable_copy_input = {
    'onCopy': 'return false;',
    'onDrag': 'return false;',
    'onDrop': 'return false;',
    'onPaste': 'return false;',
    'autocomplete': 'off',
    'class': 'form-control'
}


class CreateCenterForm(ModelForm):
    MANDATORY_FIELDS = ['name', 'office', 'code', 'tally']

    class Meta:
        model = Center
        fields = localized_fields = [
            'center_type',
            'code',
            'latitude',
            'longitude',
            'mahalla',
            'name',
            'tally',
            'office',
            'region',
            'village',
        ]

        widgets = {
            "tally": forms.HiddenInput(),
            'mahalla': Textarea(attrs={'cols': 60, 'rows': 2}),
            'name': Textarea(attrs={'cols': 60, 'rows': 2}),
            'region': Textarea(attrs={'cols': 60, 'rows': 2}),
            'village': Textarea(attrs={'cols': 60, 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super(CreateCenterForm, self).__init__(*args, **kwargs)
