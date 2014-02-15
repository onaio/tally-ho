from django.forms import ModelForm
from libya_tally.apps.tally.models import ResultForm


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
        fields = ['barcode',
                  'ballot',
                  'center',
                  'name',
                  'office',
                  'serial_number',
                  'gender',
                  'station_number']
