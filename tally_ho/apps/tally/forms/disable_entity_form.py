from django import forms
from django.utils.translation import ugettext_lazy as _

from tally_ho.apps.tally.models.center import Center
from tally_ho.apps.tally.models.station import Station
from tally_ho.libs.models.dependencies import check_results_for_forms
from tally_ho.libs.models.enums.disable_reason import DisableReason
from tally_ho.libs.validators import MinLengthValidator
from tally_ho.libs.utils.functions import disableEnableEntity

class DisableEntityForm(forms.Form):

    disableReason = forms.TypedChoiceField(choices=DisableReason.choices(),
        error_messages={'invalid': _(u"Expecting one option selected")},
        widget=forms.RadioSelect,
        label=_(u"Select a reason"),
        coerce=int)

    centerCodeInput = forms.CharField(
      required=True,
      widget = forms.HiddenInput()
    )

    stationNumberInput = forms.CharField(
      required=False,
      widget=forms.HiddenInput()
    )


    def __init__(self, *args, **kwargs):
        super(DisableEntityForm, self).__init__(*args, **kwargs)
        self.fields['disableReason'].widget.attrs['autofocus'] = 'on'


    def clean(self):
        if self.is_valid():
            cleaned_data = super(DisableEntityForm, self).clean()
            centerCode = cleaned_data.get('centerCodeInput')
            stationNumber = cleaned_data.get('stationNumberInput')
            disableReason = cleaned_data.get('disableReason')

            try:
                if stationNumber:
                  entities = Station.objects.get(station_number = stationNumber, center__code = centerCode)
                else:
                  entities = Center.objects.get(code = centerCode)
            except Center.DoesNotExist:
                raise forms.ValidationError(u"Center Number does not exist")
            except Station.DoesNotExist:
                raise forms.ValidationError(u"Station Number does not exist")

            return cleaned_data


    def save(self):
        if self.is_valid():
            centerCode = self.cleaned_data.get('centerCodeInput')
            stationNumber = self.cleaned_data.get('stationNumberInput')
            disableReason = self.cleaned_data.get('disableReason')

            return disableEnableEntity(centerCode, stationNumber, disableReason)

