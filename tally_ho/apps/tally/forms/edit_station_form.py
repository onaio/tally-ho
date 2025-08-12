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


class EditStationForm(ModelForm):
    MANDATORY_FIELDS = []

    class Meta:
        model = Station
        fields = [
            'gender',
            'registrants',
            'disable_reason',
        ]

    def __init__(self, *args, **kwargs):
        super(EditStationForm, self).__init__(*args, **kwargs)

        if self.instance.active:
            self.fields.pop('disable_reason')

        for key in self.fields:
            if key not in self.MANDATORY_FIELDS:
                self.fields[key].required = False
        self.fields['gender'].choices = self.fields['gender'].choices[:-1]
