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
        fields = ['name', 'value', 'percentage', 'active', 'description']

    def __init__(self, *args, **kargs):
        super(QuarantineCheckForm, self).__init__(*args, **kargs)
        self.fields['name'].widget.attrs.update({'class': 'form-control'})

        if self.initial['value'] == 0:
            self.fields['value'].widget.attrs.update(
                {'class': 'form-control', 'disabled': ''})
        else:
            self.fields['value'].widget.attrs.update(
                {'class': 'form-control'})

        if self.initial['percentage'] == 0:
            self.fields['percentage'].widget.attrs.update(
                {'class': 'form-control', 'disabled': ''})
        else:
            self.fields['percentage'].widget.attrs.update(
                {'class': 'form-control'})

        self.fields['description'].widget.attrs.update(
            {'class': 'form-control'})
