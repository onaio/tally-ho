from django import forms
from django.utils.translation import ugettext as _

from tally_system.apps.tally.models.result_form import ResultForm


class PassToQualityControlForm(forms.Form):
    result_form = forms.IntegerField()
    pass_to_quality_control = forms.CharField(max_length=4)

    def clean(self):
        if self.is_valid():
            cleaned_data = super(PassToQualityControlForm, self).clean()
            pk = cleaned_data.get('result_form')

            try:
                ResultForm.objects.get(pk=pk)
            except ResultForm.DoesNotExist:
                raise forms.ValidationError(
                    _(u"Result Form with key %s does not exit." % pk))

            pass_to_quality_control = cleaned_data.get(
                'pass_to_quality_control')

            if pass_to_quality_control != 'true':
                raise forms.ValidationError(
                    _(u"Suspicious activity detected."))

            return cleaned_data
