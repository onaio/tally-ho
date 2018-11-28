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


class EditCenterForm(ModelForm):
    MANDATORY_FIELDS = ['name', 'office']

    class Meta:
        model = Center
        fields = localized_fields = [
            'center_type',
            'latitude',
            'longitude',
            'mahalla',
            'name',
            'office',
            'region',
            'village',
            'disable_reason',
        ]

        widgets = {
            'mahalla': Textarea(attrs={'cols': 60, 'rows': 2}),
            'name': Textarea(attrs={'cols': 60, 'rows': 2}),
            'region': Textarea(attrs={'cols': 60, 'rows': 2}),
            'village': Textarea(attrs={'cols': 60, 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super(EditCenterForm, self).__init__(*args, **kwargs)

        if self.instance.active:
            self.fields.pop('disable_reason')

        for key in self.fields:
            if key not in self.MANDATORY_FIELDS:
                self.fields[key].required = False
