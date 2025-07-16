import reversion
from django.db import models
from django.db.models import IntegerField, OuterRef, Subquery
from django.utils.translation import gettext_lazy as _
from enumfields import EnumIntegerField

from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.apps.tally.models.station import Station
from tally_ho.apps.tally.models.user_profile import UserProfile
from tally_ho.apps.tally.models.workflow_request import WorkflowRequest
from tally_ho.libs.models.base_model import BaseModel
from tally_ho.libs.models.enums.entry_version import EntryVersion


class ReconciliationFormSet(models.QuerySet):
    def get_registrants_and_votes_type(self):
        """
        Use result form station number to get station registrants and gender

        returns: station registrants and gender
        """
        station_query = Station.objects.filter(
            station_number=OuterRef("result_form__station_number")
        )

        return self.annotate(
            voters_gender_type=Subquery(
                station_query.values("gender")[:1],
                output_field=models.CharField(),
            )
        ).annotate(
            number_of_registrants=Subquery(
                station_query.values("registrants")[:1],
                output_field=IntegerField(),
            )
        )


class ReconciliationForm(BaseModel):
    class Meta:
        app_label = "tally"

    result_form = models.ForeignKey(ResultForm, on_delete=models.PROTECT)
    user = models.ForeignKey(UserProfile, on_delete=models.PROTECT)

    active = models.BooleanField(default=True)
    entry_version = EnumIntegerField(EntryVersion)
    ballot_number_from = models.CharField(
        _("from:"), max_length=256, null=True
    )
    ballot_number_to = models.CharField(_("to:"), max_length=256, null=True)
    number_of_voters = models.PositiveIntegerField(
        _("Number of voters in the station's voter register"
          " (in addition to additional voters)")
    )
    number_of_voter_cards_in_the_ballot_box = models.PositiveIntegerField(
        _("Number of voter cards in the ballot box"), default=0
    )
    number_invalid_votes = models.PositiveIntegerField(
        _("Number of invalid votes")
    )
    number_valid_votes = models.PositiveIntegerField(
        _("Number of valid votes")
    )
    number_sorted_and_counted = models.PositiveIntegerField(
        _("Total number of the sorted and counted ballots")
    )
    notes = models.TextField(null=True, blank=True)
    objects = ReconciliationFormSet.as_manager()
    deactivated_by_request = models.ForeignKey(
        WorkflowRequest,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="deactivated_recons",
        help_text=_(
            str(
                "The workflow request that triggered the "
                "deactivation of this reconciliation record."
            )
        ),
    )

    @property
    def number_ballots_used(self):
        """Calculate the number of ballots used based on this forms.

        :returns: A positive integer representing the number of ballots used.
        """
        votes = self.result_form.num_votes

        return self.number_invalid_votes + votes

    @property
    def number_ballots_expected(self):
        """Calculate the number of ballots expected based on this form.

        :returns: A positive integer representing the number of ballots
            expected.
        """
        return self.number_of_voters - self.number_invalid_votes

    @property
    def number_ballots_inside_the_box(self):
        """Calculate the number of ballots inside the box based on this form.

        :returns: A positive integer representing the number of ballots
            inside.
        """

        return self.number_valid_votes + self.number_invalid_votes

    @property
    def number_ballots_outside_the_box(self):
        """Calculate the number of ballots outside inside the box based
        on this form.

        :returns: A positive integer representing the number of ballots
            outside.
        """

        return self.number_invalid_votes


reversion.register(ReconciliationForm)
