from django import forms
from django.utils.translation import ugettext as _

from libya_tally.apps.tally.models.center import Center


disable_copy_input = {
    'onCopy': 'return false;',
    'onDrag': 'return false;',
    'onDrop': 'return false;',
    'onPaste': 'return false;',
    'autocomplete': 'off'
}


class CenterDetailsForm(forms.Form):
    center_number = forms.CharField(min_length=5, max_length=5,
                                    widget=forms.TextInput(
                                        attrs=disable_copy_input))
    center_number_copy = forms.CharField(min_length=5, max_length=5,
                                         widget=forms.TextInput(
                                             attrs=disable_copy_input))
    station_number = forms.IntegerField(min_value=1, max_value=8,
                                        widget=forms.TextInput(
                                            attrs=disable_copy_input))
    station_number_copy = forms.IntegerField(min_value=1, max_value=8,
                                             widget=forms.TextInput(
                                                 attrs=disable_copy_input))

    def clean(self):
        if self.is_valid():
            cleaned_data = super(CenterDetailsForm, self).clean()
            center_number = cleaned_data.get('center_number')
            center_number_copy = cleaned_data.get('center_number_copy')
            station_number = cleaned_data.get('station_number')
            station_number_copy = cleaned_data.get('station_number_copy')

            if center_number != center_number_copy:
                raise forms.ValidationError(_(u"Center Numbers do not match"))

            if station_number != station_number_copy:
                raise forms.ValidationError(_(u"Station Numbers do not match"))

            try:
                center = Center.objects.get(code=center_number)
                stations = center.stations.all()
                valid_station_numbers = [s.station_number for s in stations]

                if not int(station_number) in valid_station_numbers:
                    raise forms.ValidationError(_(
                        u"Invalid Station Number for this Center"))

            except Center.DoesNotExist:
                raise forms.ValidationError(u"Center Number does not exist")

            return cleaned_data
