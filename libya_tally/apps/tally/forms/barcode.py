from django import forms


class IntakeBarcodeForm(forms.Form):
    barcode = forms.CharField(max_length=9, min_length=9)
    barcode_copy = forms.CharField(max_length=9, min_length=9)
