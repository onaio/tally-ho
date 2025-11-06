from django import forms
from django.forms import ModelForm, Textarea
from tally_ho.apps.tally.models.center import Center


class CreateCenterForm(ModelForm):
    class Meta:
        model = Center
        fields = localized_fields = [
            "center_type",
            "code",
            "latitude",
            "longitude",
            "mahalla",
            "name",
            "tally",
            "office",
            "region",
            "village",
        ]

        widgets = {
            "tally": forms.HiddenInput(),
            "mahalla": Textarea(attrs={"cols": 60, "rows": 2}),
            "name": Textarea(attrs={"cols": 60, "rows": 2}),
            "region": Textarea(attrs={"cols": 60, "rows": 2}),
            "village": Textarea(attrs={"cols": 60, "rows": 2}),
        }
