from django.forms import ModelForm
from tally_system.apps.tally.models import ResultForm


disable_copy_input = {
    'onCopy': 'return false;',
    'onDrag': 'return false;',
    'onDrop': 'return false;',
    'onPaste': 'return false;',
    'autocomplete': 'off',
    'class': 'form-control'
}


class NewResultForm(ModelForm):
    class Meta:
        model = ResultForm
        fields = localized_fields = ['ballot',
                                     'center',
                                     'office',
                                     'gender',
                                     'station_number']
