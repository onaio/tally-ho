from django.db import models
from django.db.models import Subquery, OuterRef, IntegerField
from enumfields import EnumIntegerField
from django.utils.translation import gettext_lazy as _
import reversion

from tally_ho.apps.tally.models.station import Station
from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.apps.tally.models.user_profile import UserProfile
from tally_ho.libs.models.base_model import BaseModel
from tally_ho.libs.models.enums.entry_version import EntryVersion


class ReconciliationFormSet(models.QuerySet):
    def get_registrants_and_votes_type(self):
        """
        Use result form station number to get station registrants and gender

        returns: station registrants and gender
        """
        station_query = (
            Station.objects.filter(
                station_number=OuterRef('result_form__station_number'))
        )

        return self.annotate(
            voters_gender_type=Subquery(
                station_query.values('gender')[:1],
                output_field=models.CharField()
            )
        ).annotate(
            number_of_registrants=Subquery(
                station_query.values('registrants')[:1],
                output_field=IntegerField()
            )
        )


class ReconciliationForm(BaseModel):
    class Meta:
        app_label = 'tally'

    result_form = models.ForeignKey(ResultForm, on_delete=models.PROTECT)
    user = models.ForeignKey(UserProfile, on_delete=models.PROTECT)

    active = models.BooleanField(default=True)
    entry_version = EnumIntegerField(EntryVersion)
    ballot_number_from = models.CharField(_('from:'), max_length=256)
    ballot_number_to = models.CharField(_('to:'), max_length=256)
    is_stamped = models.BooleanField(_('Is the form stamped?'))
    number_ballots_received = models.PositiveIntegerField(
        _('Total number of ballots received by the polling station'))
    number_of_voter_cards_in_the_ballot_box = models.PositiveIntegerField(
        _('Number of voter cards in the ballot box'), default=0)
    number_unused_ballots = models.PositiveIntegerField(
        _('Number of unused ballots'))
    number_spoiled_ballots = models.PositiveIntegerField(
        _('Number of spoiled ballots'))
    number_cancelled_ballots = models.PositiveIntegerField(
        _('Number of cancelled ballots'))
    number_ballots_outside_box = models.PositiveIntegerField(
        _('Total number of ballots remaining outside the ballot box'))
    number_ballots_inside_box = models.PositiveIntegerField(
        _('Number of ballots found inside the ballot box'))
    number_ballots_inside_and_outside_box = models.PositiveIntegerField(
        _('Total number of ballots found inside and outside the ballot box'))
    number_unstamped_ballots = models.PositiveIntegerField(
        _('Number of unstamped ballots'))
    number_invalid_votes = models.PositiveIntegerField(
        _('Number of invalid votes'))
    number_valid_votes = models.PositiveIntegerField(
        _('Number of valid votes'))
    number_sorted_and_counted = models.PositiveIntegerField(
        _('Total number of the sorted and counted ballots'))
    signature_polling_officer_1 = models.BooleanField(
        _('Is the form signed by polling officer 1?'))
    signature_polling_officer_2 = models.BooleanField(
        _('Is the form signed by polling officer 2?'))
    signature_polling_station_chair = models.BooleanField(
        _('Is the form signed by the polling station chair?'))
    signature_dated = models.BooleanField(_('Is the form dated?'))
    objects = ReconciliationFormSet.as_manager()

    @property
    def number_ballots_used(self):
        """Calculate the number of ballots used based on this forms.

        :returns: A positive integer representing the number of ballots used.
        """
        votes = self.result_form.num_votes

        return (self.number_cancelled_ballots +
                self.number_unstamped_ballots +
                self.number_invalid_votes +
                votes)

    @property
    def number_ballots_expected(self):
        """Calculate the number of ballots expected based on this form.

        :returns: A positive integer representing the number of ballots
            expected.
        """
        return (self.number_ballots_inside_box -
                self.number_unstamped_ballots -
                self.number_invalid_votes)

    @property
    def number_ballots_inside_the_box(self):
        """Calculate the number of ballots inside the box based on this form.

        :returns: A positive integer representing the number of ballots
            inside.
        """

        return (self.number_valid_votes +
                self.number_invalid_votes +
                self.number_unstamped_ballots)

    @property
    def number_ballots_outside_the_box(self):
        """Calculate the number of ballots outside inside the box based
        on this form.

        :returns: A positive integer representing the number of ballots
            outside.
        """

        return (self.number_unused_ballots +
                self.number_cancelled_ballots +
                self.number_spoiled_ballots)


reversion.register(ReconciliationForm)
