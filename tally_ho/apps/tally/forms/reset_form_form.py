from django import forms
from django.utils.translation import gettext_lazy as _


from tally_ho.apps.tally.models.result_form import ResultForm


disable_copy_input = {
    'onCopy': 'return false;',
    'onDrag': 'return false;',
    'onDrop': 'return false;',
    'onPaste': 'return false;',
    'autocomplete': 'off',
    'class': 'form-control'
}


class ResetFormForm(forms.Form):
    barcode = forms.CharField(
        max_length=255,
        error_messages={
            'required': _("Barcode is required")
        },
        widget=forms.TextInput(attrs=disable_copy_input),
        label=_("Form Barcode")
    )

    tally_id = forms.IntegerField(widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        super(ResetFormForm, self).__init__(*args, **kwargs)
        self.fields['barcode'].widget.attrs['autofocus'] = 'on'

    def save(self):
        if self.is_valid():
            barcode = self.cleaned_data.get('barcode')
            tally_id = self.cleaned_data.get('tally_id')
            try:
                result_form = ResultForm.objects.get(
                    barcode=barcode,
                    tally__id=tally_id
                )
            except ResultForm.DoesNotExist:
                raise forms.ValidationError(_('Form not found'))
            else:
                return result_form
