from django.forms import ModelForm
from tally_ho.apps.tally.models.ballot import Ballot

disable_copy_input = {
    'onCopy': 'return false;',
    'onDrag': 'return false;',
    'onDrop': 'return false;',
    'onPaste': 'return false;',
    'autocomplete': 'off',
    'class': 'form-control'
}


class EditRaceForm(ModelForm):
    MANDATORY_FIELDS = []

    class Meta:
        model = Ballot
        fields = localized_fields = [
            'number',
            'race_type',
            'active',
            'disable_reason',
            'available_for_release',
        ]

    def __init__(self, *args, **kwargs):
        super(EditRaceForm, self).__init__(*args, **kwargs)

        if self.instance.active:
            self.fields.pop('disable_reason')

        for key in self.fields:
            if key not in self.MANDATORY_FIELDS:
                self.fields[key].required = False
