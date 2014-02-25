from django import forms
from django.utils.translation import ugettext_lazy as _

from libya_tally.apps.tally.models.center import Center
from libya_tally.libs.validators import MinLengthValidator


disable_copy_input = {
    'onCopy': 'return false;',
    'onDrag': 'return false;',
    'onDrop': 'return false;',
    'onPaste': 'return false;',
    'autocomplete': 'off',
    'class': 'form-control'
}
min_station_value = 1
max_station_value = 53


class RemoveCenterForm(forms.Form):
    validators = [MinLengthValidator(5)]

    center_number = forms.IntegerField(
        error_messages={
            'invalid': _(u"Expecting only numbers for center number")},
        validators=validators,
        widget=forms.NumberInput(attrs=disable_copy_input),
        label=_(u"Center Number"))

    def __init__(self, *args, **kwargs):
        super(RemoveCenterForm, self).__init__(*args, **kwargs)
        self.fields['center_number'].widget.attrs['autofocus'] = 'on'

    def clean(self):
        if self.is_valid():
            cleaned_data = super(RemoveCenterForm, self).clean()
            center_number = cleaned_data.get('center_number')

            try:
                center = Center.objects.get(code=center_number)
            except Center.DoesNotExist:
                raise forms.ValidationError(u"Center Number does not exist")
            else:
                for resultform in center.resultform_set.all():
                    if resultform.results.all():
                        raise forms.ValidationError(
                            _(u"Cannot remove center, some results for"
                              u" %(barcode)s exist." % {'barcode':
                                                        resultform.barcode}))

            return cleaned_data

    def save(self):
        if self.is_valid():
            center_number = self.cleaned_data.get('center_number')
            try:
                center = Center.objects.get(code=center_number)
            except Center.DoesNotExist:
                raise forms.ValidationError(_(u"Center Number does not exist"))
            else:
                center.remove()
