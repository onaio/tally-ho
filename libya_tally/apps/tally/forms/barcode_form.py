from django import forms
from django.utils.translation import ugettext as _

from libya_tally.apps.tally.models.result_form import ResultForm
from libya_tally.libs.validators import MinLengthValidator


disable_copy_input = {
    'onCopy': 'return false;',
    'onDrag': 'return false;',
    'onDrop': 'return false;',
    'onPaste': 'return false;',
    'autocomplete': 'off',
    'class': 'form-control'
}


class BarcodeForm(forms.Form):
    barcode = forms.IntegerField(
        error_messages={'invalid': _(u"Expecting only numbers for barcodes")},
        validators=[MinLengthValidator(9)],
        widget=forms.NumberInput(
            attrs=disable_copy_input), label=_(u"Barcode"))
    barcode_copy = forms.IntegerField(
        error_messages={'invalid': _(u"Expecting only numbers for barcodes")},
        validators=[MinLengthValidator(9)],
        widget=forms.NumberInput(
            attrs=disable_copy_input), label=_(u"Barcode Copy"))

    def __init__(self, *args, **kwargs):
        super(BarcodeForm, self).__init__(*args, **kwargs)
        self.fields['barcode'].widget.attrs['autofocus'] = 'on'

    def clean(self):
        if self.is_valid():
            cleaned_data = super(BarcodeForm, self).clean()
            barcode = cleaned_data.get('barcode')
            barcode_copy = cleaned_data.get('barcode_copy')

            if barcode != barcode_copy:
                raise forms.ValidationError(_(u"Barcodes do not match!"))

            try:
                ResultForm.objects.get(barcode=barcode)
            except ResultForm.DoesNotExist:
                raise forms.ValidationError(u"Barcode does not exist")

            return cleaned_data
