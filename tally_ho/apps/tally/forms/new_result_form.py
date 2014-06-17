from django.forms import ModelForm, ValidationError
from django.utils.translation import ugettext as _

from tally_ho.apps.tally.models import ResultForm
from tally_ho.apps.tally.models.station import Station

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

    def clean(self):
        cleaned_data = super(NewResultForm, self).clean()

        cdata_keys = cleaned_data.keys()
        center = cleaned_data['center'] if 'center' in cdata_keys else None
        station_number = cleaned_data['station_number'] if 'station_number' in cdata_keys else None
        ballot = cleaned_data['ballot'] if 'ballot' in cdata_keys else None

        #TODO: enable this once enabling/disabling races is implemented
        #if ballot and not ballot.active:
        #    raise ValidationError(_('Race for ballot is disabled'))

        if center and not center.active:
            raise ValidationError(_('Selected center is disabled'))

        try:
            if station_number:
                station = Station.objects.get(station_number = station_number, center = center)

                if not station.active:
                    raise ValidationError(_('Selected station is disabled'))

        except Station.DoesNotExist:
            raise ValidationError(_('Station does no exist for the selected center'))

        return cleaned_data
