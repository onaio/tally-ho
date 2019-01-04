from django import forms
from django.forms import ModelForm
from django.utils.translation import ugettext_lazy as _

from tally_ho.apps.tally.models.ballot import Ballot
from tally_ho.apps.tally.models.comment import Comment

disable_copy_input = {
    'onCopy': 'return false;',
    'onDrag': 'return false;',
    'onDrop': 'return false;',
    'onPaste': 'return false;',
    'autocomplete': 'off',
    'class': 'form-control'
}


class EditRaceForm(ModelForm):
    class Meta:
        model = Ballot
        fields = localized_fields = [
            'number',
            'race_type',
            'active',
            'disable_reason',
            'available_for_release',
        ]

    comment_input = forms.CharField(
        required=False,
        label=_("Add a new comments"),
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
                raise forms.ValidationError(_(u"Race does not exist"))
            else:
                tally_id = self.cleaned_data.get('tally_id')
                comment = self.cleaned_data.get('comment_input')

                if comment:
                    Comment(text=comment,
                            ballot=race,
                            tally_id=tally_id).save()

            return super(EditRaceForm, self).save()
