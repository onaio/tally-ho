from django.forms import (
    ModelForm,
    ValidationError,
    IntegerField,
    HiddenInput,
    ModelChoiceField,
)
from django.utils.translation import ugettext as _

from tally_ho.apps.tally.models import ResultForm
from tally_ho.apps.tally.models.station import Station
from tally_ho.apps.tally.models.center import Center
from tally_ho.apps.tally.models.office import Office
from tally_ho.apps.tally.models.ballot import Ballot

disable_copy_input = {
    'onCopy': 'return false;',
    'onDrag': 'return false;',
    'onDrop': 'return false;',
    'onPaste': 'return false;',
    'autocomplete': 'off',
    'class': 'form-control'
}


class NewResultForm(ModelForm):
    class Meta:
        model = ResultForm
        fields = localized_fields = ['ballot',
                                     'center',
                                     'office',
                                     'gender',
                                     'station_number']

    tally_id = IntegerField(widget=HiddenInput())

    def __init__(self, *args, **kwargs):
        super(NewResultForm, self).__init__(*args, **kwargs)

        if self.initial.get('tally_id'):
            self.fields['center'] = ModelChoiceField(
                queryset=Center.objects.filter(
                    tally__id=self.initial['tally_id']))
            self.fields['office'] = ModelChoiceField(
                queryset=Office.objects.filter(
                    tally__id=self.initial['tally_id']))
            self.fields['ballot'] = ModelChoiceField(
                queryset=Ballot.objects.filter(
                    tally__id=self.initial['tally_id']))

    def clean(self):
        cleaned_data = super(NewResultForm, self).clean()

        center = cleaned_data.get('center', None)
        station_number = cleaned_data.get('station_number', None)
        ballot = cleaned_data.get('ballot', None)

        if not center or not station_number or not ballot:
            raise ValidationError(_('All fields are mandatory'))

        # TODO: enable this once enabling/disabling races is implemented
        # if ballot and not ballot.active:
        #     raise ValidationError(_('Race for ballot is disabled'))

        if center and not center.active:
            raise ValidationError(_('Selected center is disabled'))

        try:
            if station_number:
                station = Station.objects.get(station_number=station_number,
                                              center=center)

                if not station.active:
                    raise ValidationError(_('Selected station is disabled'))

        except Station.DoesNotExist:
            raise ValidationError(
                _('Station does no exist for the selected center'))

        if center.sub_constituency and \
                ballot.number != center.sub_constituency.code:
            raise ValidationError(
                _('Ballot number do not match for center and station'))

        return cleaned_data
