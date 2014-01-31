from django import forms
from django.utils.translation import ugettext as _

from libya_tally.apps.tally.models.result_form import ResultForm


class IntakeBarcodeForm(forms.Form):
    barcode = forms.CharField(max_length=9, min_length=9)
    barcode_copy = forms.CharField(max_length=9, min_length=9)

    def clean(self):
        cleaned_data = super(IntakeBarcodeForm, self).clean()
        barcode = cleaned_data.get('barcode')
        barcode_copy = cleaned_data.get('barcode_copy')

        if barcode != barcode_copy:
            raise forms.ValidationError(_(u"Barcodes do not match!"))

        try:
            ResultForm.objects.get(barcode=barcode)
        except ResultForm.DoesNotExist:
            raise forms.ValidationError(u"Barcode does not exist")
        return cleaned_data
