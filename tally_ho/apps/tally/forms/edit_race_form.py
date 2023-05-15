from django import forms
from django.forms import ModelForm
from tally_ho.apps.tally.forms.fields import RestrictedFileField
from django.utils.translation import gettext_lazy as _

from tally_ho.apps.tally.models.ballot import Ballot
from tally_ho.apps.tally.models.comment import Comment


class EditRaceForm(ModelForm):
    class Meta:
        model = Ballot
        fields = localized_fields = [
            'number',
            'race_type',
            'active',
            'disable_reason',
            'available_for_release',
            'document',
        ]

    document = RestrictedFileField(required=False)

    comment_input = forms.CharField(
        required=False,
        label=_("Add new comments"),
        widget=forms.Textarea(attrs={'cols': 80, 'rows': 5}),
    )

    tally_id = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
    )

    race_id = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
    )

    def __init__(self, *args, **kwargs):
        super(EditRaceForm, self).__init__(*args, **kwargs)

        if self.instance.active:
            self.fields.pop('disable_reason')

    def save(self):
        if self.is_valid():
            race_id = self.cleaned_data.get('race_id')
            race = None

            try:
                race = Ballot.objects.get(id=race_id)
            except Ballot.DoesNotExist:
                raise forms.ValidationError(_('Race does not exist'))
            else:
                tally_id = self.cleaned_data.get('tally_id')
                comment = self.cleaned_data.get('comment_input')

                if comment:
                    Comment(text=comment,
                            ballot=race,
                            tally_id=tally_id).save()

            return super(EditRaceForm, self).save()
