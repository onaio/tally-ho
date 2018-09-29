from django import forms
from django.utils.translation import ugettext_lazy as _

from tally_ho.apps.tally.models.center import Center
from tally_ho.apps.tally.models.station import Station
from tally_ho.apps.tally.models.ballot import Ballot
from tally_ho.libs.models.enums.disable_reason import DisableReason
from tally_ho.libs.utils.functions import (
    disableEnableEntity,
    disableEnableRace,
)


class DisableEntityForm(forms.Form):
    disableReason = forms.TypedChoiceField(
        choices=DisableReason.choices(),
        error_messages={'invalid': _(u"Expecting one option selected")},
        widget=forms.RadioSelect,
        label=_(u"Select a reason"),
        coerce=int,
    )

    tally_id = forms.CharField(
      required=False,
      widget=forms.HiddenInput(),
    )

    centerCodeInput = forms.CharField(
      required=False,
      widget=forms.HiddenInput(),
    )

    stationNumberInput = forms.CharField(
      required=False,
      widget=forms.HiddenInput(),
    )

    raceIdInput = forms.CharField(
      required=False,
      widget=forms.HiddenInput(),
    )

    def __init__(self, *args, **kwargs):
        super(DisableEntityForm, self).__init__(*args, **kwargs)
        self.fields['disableReason'].widget.attrs['autofocus'] = 'on'

    def clean(self):
        if self.is_valid():
            cleaned_data = super(DisableEntityForm, self).clean()
            tally_id = cleaned_data.get('tally_id')
            center_code = cleaned_data.get('centerCodeInput')
            station_number = cleaned_data.get('stationNumberInput')
            race_id = cleaned_data.get('raceIdInput')

            if center_code:
                try:
                    if station_number:
                        Station.objects.get(
                            station_number=station_number,
                            center__code=center_code,
                            center__tally__id=tally_id)
                    else:
                        Center.objects.get(tally__id=tally_id,
                                           code=center_code)
                except Center.DoesNotExist:
                    raise forms.ValidationError(
                        u"Center Number does not exist")
                except Station.DoesNotExist:
                    raise forms.ValidationError(
                        u"Station Number does not exist")
            elif race_id:
                try:
                    Ballot.objects.get(id=race_id)
                except Ballot.DoesNotExist:
                    raise forms.ValidationError(u"Race does not exist")
            else:
                raise forms.ValidationError(u"Error")

            return cleaned_data

    def save(self):
        if self.is_valid():
            tally_id = self.cleaned_data.get('tally_id')
            center_code = self.cleaned_data.get('centerCodeInput')
            station_number = self.cleaned_data.get('stationNumberInput')
            race_id = self.cleaned_data.get('raceIdInput')
            disable_reason = self.cleaned_data.get('disableReason')

            result = None

            if not race_id:
                result = disableEnableEntity(center_code,
                                             station_number,
                                             disable_reason,
                                             tally_id)
            else:
                result = disableEnableRace(race_id, disable_reason)

            return result
