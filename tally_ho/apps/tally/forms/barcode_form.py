from django import forms
from django.core.validators import MinLengthValidator, MaxLengthValidator,\
    RegexValidator
from django.utils.translation import ugettext as _

from tally_ho.apps.tally.models.result_form import ResultForm


disable_copy_input = {
    'onCopy': 'return false;',
    'onDrag': 'return false;',
    'onDrop': 'return false;',
    'onPaste': 'return false;',
    'autocomplete': 'off',
    'class': 'form-control'
}


class BarcodeForm(forms.Form):
    error_messages = {'invalid': _(u"Expecting only numbers for barcodes")}
    validators = [MaxLengthValidator(9), MinLengthValidator(9), RegexValidator(
        regex=r'^[0-9]*$', message=_(u"Expecting only numbers for barcodes"))]

    barcode = forms.CharField(
        error_messages=error_messages,
        validators=validators,
        widget=forms.NumberInput(
            attrs=disable_copy_input), label=_(u"Barcode"))
    barcode_copy = forms.CharField(
        error_messages=error_messages,
        validators=validators,
        widget=forms.NumberInput(
            attrs=disable_copy_input), label=_(u"Barcode Copy"))

    def __init__(self, *args, **kwargs):
        super(BarcodeForm, self).__init__(*args, **kwargs)
        self.fields['barcode'].widget.attrs['autofocus'] = 'on'

    def clean(self):
        """Verify that barcode and barcode copy match and that the barcode is
        for a result form in the system.
        """
        if self.is_valid():
            cleaned_data = super(BarcodeForm, self).clean()
            barcode = cleaned_data.get('barcode')
            barcode_copy = cleaned_data.get('barcode_copy')

            if barcode != barcode_copy:
                raise forms.ValidationError(_(u"Barcodes do not match!"))

            try:
                ResultForm.objects.get(barcode=barcode)
            except ResultForm.DoesNotExist:
                raise forms.ValidationError(_(u"Barcode does not exist."))

            return cleaned_data
