from django import forms

from tally_ho.apps.tally.forms.constants import DISABLE_COPY_INPUT


class CandidateForm(forms.Form):
    # Extend the DISABLE_COPY_INPUT attrs to include 'required' class
    votes_attrs = DISABLE_COPY_INPUT.copy()
    votes_attrs["class"] = "form-control required"

    votes = forms.IntegerField(
        min_value=0, required=True, widget=forms.TextInput(attrs=votes_attrs), label=""
    )
