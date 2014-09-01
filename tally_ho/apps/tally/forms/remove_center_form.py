from django import forms
from django.conf import settings
from django.utils.translation import ugettext_lazy as _


from tally_ho.apps.tally.models.center import Center
from tally_ho.libs.models.dependencies import check_results_for_forms
from tally_ho.libs.validators import MinLengthValidator


disable_copy_input = {
    'onCopy': 'return false;',
    'onDrag': 'return false;',
    'onDrop': 'return false;',
    'onPaste': 'return false;',
    'autocomplete': 'off',
    'class': 'form-control'
}

min_station_value = settings.MIN_STATION_VALUE
max_station_value = settings.MAX_STATION_VALUE


class RemoveCenterForm(forms.Form):
    validators = [MinLengthValidator(5)]

    center_number = forms.IntegerField(
        error_messages={
            'invalid': _(u"Expecting only numbers for center number")},
        validators=validators,
        widget=forms.NumberInput(attrs=disable_copy_input),
        label=_(u"Center Number"))

    tally_id = forms.IntegerField(widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        super(RemoveCenterForm, self).__init__(*args, **kwargs)
        self.fields['center_number'].widget.attrs['autofocus'] = 'on'

    def clean(self):
        if self.is_valid():
            cleaned_data = super(RemoveCenterForm, self).clean()
            center_number = cleaned_data.get('center_number')
            tally_id = cleaned_data.get('tally_id')

            try:
                center = Center.objects.get(code=center_number, tally__id=tally_id)
            except Center.DoesNotExist:
                raise forms.ValidationError(u"Center Number does not exist")
            else:
                check_results_for_forms(center.resultform_set.all())

            return cleaned_data

    def save(self):
        if self.is_valid():
            center_number = self.cleaned_data.get('center_number')
            tally_id = self.cleaned_data.get('tally_id')
            try:
                center = Center.objects.get(code=center_number, tally__id=tally_id)
            except Center.DoesNotExist:
                raise forms.ValidationError(_(u"Center Number does not exist"))
            else:
                return center
