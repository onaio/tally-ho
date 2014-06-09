from django import forms
from django.utils.translation import ugettext_lazy as _

from tally_ho.apps.tally.models.center import Center
from tally_ho.apps.tally.models.station import Station
from tally_ho.libs.models.dependencies import check_results_for_forms
from tally_ho.libs.models.enums.disable_reason import DisableReason
from tally_ho.libs.validators import MinLengthValidator

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
        print "En el constructor"
        super(DisableEntityForm, self).__init__(*args, **kwargs)
        print "En el constructor 2"
        self.fields['disableReason'].widget.attrs['autofocus'] = 'on'
        print "En el constructor 3"

    def clean(self):
        print "Entra en clean"
        if self.is_valid():
            print "Entra en clean 1"
            cleaned_data = super(DisableEntityForm, self).clean()
            print "Entra en clean 2"
            centerCode = cleaned_data.get('centerCodeInput')
            print "Entra en clean 3"
            stationNumber = cleaned_data.get('stationNumberInput')
            print "Entra en clean 4"
            disableReason = cleaned_data.get('disableReason')
            print "Entra en clean 5"

            print "Vamos por aqui"

            try:
                if stationNumber:
                  entities = Station.objects.get(station_number = stationNumber, center__code = centerCode)
                else:
                  entities = Center.objects.get(code = centerCode)
            except Center.DoesNotExist:
                raise forms.ValidationError(u"Center Number does not exist")
            except Station.DoesNotExist:
                raise forms.ValidationError(u"Station Number does not exist")

            print "Todo va bien"
            return cleaned_data

    def save(self):
        print "Entra en el save"
        if self.is_valid():
            print self.cleaned_data
            centerCode = self.cleaned_data.get('centerCodeInput')
            stationNumber = self.cleaned_data.get('stationNumberInput')
            print "centerCode: %s" % centerCode
            entities = []
            entity_to_return = None
            try:
              if stationNumber:
                  entity_to_return = Station.objects.get(station_number = stationNumber, center__code = centerCode)
                  entities.append(entity_to_return)
              else:
                  print "Entra en el else"
                  entity_to_return = Center.objects.get(code= centerCode)
                  entities.append(entity_to_return)
                  entities += Station.objects.filter(center__code = centerCode)
            except Center.DoesNotExist:
                raise forms.ValidationError(_(u"Center Number does not exist"))
            except Station.DoesNotExist:
                raise forms.ValidationError(_(u"Station Number does not exist"))
            else:
                print "try-else"
                for oneEntity in entities:
                    oneEntity.active = False
                    print "disable-reason"
                    oneEntity.disable_reason = self.cleaned_data.get('disableReason')
                    print "Antes de entityy save"
                    oneEntity.save()
                return entity_to_return
