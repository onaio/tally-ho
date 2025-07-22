from django.core.exceptions import ValidationError
from django.forms import ModelForm
from django.utils.translation import gettext_lazy as _

from tally_ho.apps.tally.models import ReconciliationForm

disable_copy_input = {
    "onCopy": "return false;",
    "onDrag": "return false;",
    "onDrop": "return false;",
    "onPaste": "return false;",
    "autocomplete": "off",
    "class": "form-control",
}


class ReconForm(ModelForm):
    class Meta:
        model = ReconciliationForm
        fields = localized_fields = [
            "number_of_voters",
            "number_of_voter_cards_in_the_ballot_box",
            "number_invalid_votes",
            "number_valid_votes",
            "number_sorted_and_counted",
            "notes",
        ]
        localized_fields = "__all__"

    def __init__(self, *args, **kwargs):
        super(ReconForm, self).__init__(*args, **kwargs)

        for field in self.fields:
            for k, v in list(disable_copy_input.items()):
                self.fields[field].widget.attrs[k] = v

            class_str = ""
            if field != "notes" and self.fields[field].required:
                class_str = "required"

            if self.fields[field].widget.attrs.get("class"):
                class_str = "%s %s" % (
                    class_str,
                    self.fields[field].widget.attrs.get("class"),
                )
            self.fields[field].widget.attrs["class"] = class_str

    def clean(self):
        cleaned_data = super(ReconForm, self).clean()

        all_zero = True
        has_data = False

        recon_fields = [
            "number_of_voters",
            "number_of_voter_cards_in_the_ballot_box",
            "number_invalid_votes",
            "number_valid_votes",
            "number_sorted_and_counted",
        ]

        for field in recon_fields:
            value = cleaned_data.get(field)
            if value is not None and str(value).strip():
                has_data = True
                if int(value) > 0:
                    all_zero = False
                    break

        if not has_data or all_zero:
            raise ValidationError(
                _(
                    str(
                        "All reconciliation fields are blank or zero."
                        " Form must be marked for Clearance."
                    )
                )
            )

        return cleaned_data
