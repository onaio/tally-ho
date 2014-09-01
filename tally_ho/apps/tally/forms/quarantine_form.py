from django.forms import ModelForm

from tally_ho.apps.tally.models.quarantine_check import QuarantineCheck


disable_copy_input = {
    'onCopy': 'return false;',
    'onDrag': 'return false;',
    'onDrop': 'return false;',
    'onPaste': 'return false;',
    'autocomplete': 'off',
    'class': 'form-control required'
}


class QuarantineCheckForm(ModelForm):
    class Meta:
        model = QuarantineCheck
        fields = ['name', 'value', 'percentage']

    def __init__(self, *args, **kargs):
        super(QuarantineCheckForm, self).__init__(*args, **kargs)
        self.fields['name'].widget.attrs.update({'class' : 'form-control'})
        self.fields['value'].widget.attrs.update({'class' : 'form-control'})
        self.fields['percentage'].widget.attrs.update({'class' : 'form-control'})

