from django import forms
from django.utils.translation import ugettext_lazy as _

from tally_ho.apps.tally.models.center import Center
from tally_ho.apps.tally.models.station import Station
from tally_ho.apps.tally.models.ballot import Ballot
from tally_ho.libs.models.dependencies import check_results_for_forms
from tally_ho.libs.models.enums.disable_reason import DisableReason
from tally_ho.libs.validators import MinLengthValidator
from tally_ho.libs.utils.functions import disableEnableEntity, disableEnableRace

class DisableEntityForm(forms.Form):

    disableReason = forms.TypedChoiceField(choices=DisableReason.choices(),
        error_messages={'invalid': _(u"Expecting one option selected")},
        widget=forms.RadioSelect,
        label=_(u"Select a reason"),
        coerce=int)

    tally_id = forms.CharField(
      required=False,
      widget = forms.HiddenInput()
    )

    centerCodeInput = forms.CharField(
      required=False,
      widget = forms.HiddenInput()
    )

    stationNumberInput = forms.CharField(
      required=False,
      widget=forms.HiddenInput()
    )

    raceIdInput = forms.CharField(
      required=False,
      widget=forms.HiddenInput()
    )


    def __init__(self, *args, **kwargs):
        super(DisableEntityForm, self).__init__(*args, **kwargs)
        self.fields['disableReason'].widget.attrs['autofocus'] = 'on'


    def clean(self):
        if self.is_valid():
            cleaned_data = super(DisableEntityForm, self).clean()
            tally_id = cleaned_data.get('tally_id')
            centerCode = cleaned_data.get('centerCodeInput')
            stationNumber = cleaned_data.get('stationNumberInput')
            raceId = cleaned_data.get('raceIdInput')
            disableReason = cleaned_data.get('disableReason')

            if centerCode:
                try:
                    if stationNumber:
                      entities = Station.objects.get(station_number = stationNumber,
                                                    center__code = centerCode,
                                                    center__tally__id = tally_id)
                    else:
                      entities = Center.objects.get(tally__id=tally_id, code = centerCode)
                except Center.DoesNotExist:
                    raise forms.ValidationError(u"Center Number does not exist")
                except Station.DoesNotExist:
                    raise forms.ValidationError(u"Station Number does not exist")
            elif raceId:
                try:
                    entities = Ballot.objects.get(id = raceId)
                except Ballot.DoesNotExist:
                    raise forms.ValidationError(u"Race does not exist")
            else:
                raise forms.ValidationError(u"Error")

            return cleaned_data


    def save(self):
        if self.is_valid():
            tally_id = self.cleaned_data.get('tally_id')
            centerCode = self.cleaned_data.get('centerCodeInput')
            stationNumber = self.cleaned_data.get('stationNumberInput')
            raceId = self.cleaned_data.get('raceIdInput')
            disableReason = self.cleaned_data.get('disableReason')

            result = None
            if not raceId:
                result = disableEnableEntity(centerCode, stationNumber, disableReason, tally_id)
            else:
                result = disableEnableRace(raceId, disableReason)

            return result

