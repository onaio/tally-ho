from django.db import models
from django.utils.translation import ugettext as _

from libya_tally.libs.models.base_model import BaseModel


class ReconciliationForm(BaseModel):
    result_form = models.OneToOneField('ResultForm')

    ballot_number_from = models.PositiveIntegerField(
        help_text=_('Serial number of ballots received by the polling station'
                    'from'))
    ballot_number_to = models.PositiveIntegerField(help_text=_('To'))
    number_ballots_received = models.PositiveIntegerField(
        help_text=_('Total number of ballots received by the polling station'))
    number_signatures_in_vr = models.PositiveIntegerField(
        help_text=_('Number of signatures in the VR'))
    number_unused_ballots = models.PositiveIntegerField(
        help_text=_('Number of unused ballots'))
    number_spoiled_ballots = models.PositiveIntegerField(
        help_text=_('Number of spoiled ballots'))
    number_cancelled_ballots = models.PositiveIntegerField(
        help_text=_('Number of cancelled ballots'))
    number_ballots_outside_box = models.PositiveIntegerField(
        help_text=_('Total number of ballots remaining outside the ballot box'
                    ))
    number_ballots_inside_box = models.PositiveIntegerField(
        help_text=_('Number of ballots found inside the ballot box'))
    number_ballots_inside_and_outside_box = models.PositiveIntegerField(
        help_text=_('Total number of ballots found inside and outside the '
                    'ballot box'))
    number_unstamped_ballots = models.PositiveIntegerField(
        help_text=_('Number of unstamped ballots'))
    number_invalid_votes = models.PositiveIntegerField(
        help_text=_('Number of invalid votes (including the blanks)'))
    number_valid_votes = models.PositiveIntegerField(
        help_text=_('Number of valid votes'))
    number_sorted_and_counted = models.PositiveIntegerField(
        help_text=_('Total number of the sorted and counted ballots'))
    remarks = models.TextField(blank=True, help_text=_(
        'You may use this space for any necessary remarks'))
