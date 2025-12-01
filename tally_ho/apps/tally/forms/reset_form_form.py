from django import forms
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _

from tally_ho.apps.tally.models.result_form import ResultForm

class ResetFormForm(forms.Form):
    barcode = forms.CharField( 
        min_length=11,
        max_length=11,
        required=True,
        validators=[
            RegexValidator(
                regex=r'^[0-9]{11}$',
                message=_('Please enter exactly 11 numbers'),
            ),
        ],       
        widget=forms.NumberInput(attrs={
        'class': 'form-control',
        'title': _('Please enter exactly 11 numbers'),
        'autofocus': True,
        'oninput': "this.value = this.value.replace(/[^0-9]/g, '')",
        'oncopy': 'return false;',
        'ondrag': 'return false;',
        'ondrop': 'return false;',
        'onpaste': 'return false;',
        "autocomplete": "off",
        }),
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
