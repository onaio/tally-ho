from django import forms
from django.utils.translation import gettext_lazy as _

from tally_ho.apps.tally.forms.constants import DISABLE_COPY_INPUT
from tally_ho.apps.tally.models.result_form import ResultForm

class ResetFormForm(forms.Form):
    barcode = forms.CharField(
        max_length=255,
        error_messages={
            'required': _("Barcode is required")
        },
        widget=forms.TextInput(attrs=DISABLE_COPY_INPUT),
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
