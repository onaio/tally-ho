import reversion
from django.contrib.postgres.fields import ArrayField
from django.db import models


class AllCandidatesVotes(models.Model):
    class Meta:
        app_label = 'tally'
        managed = False

    tally_id = models.IntegerField()
    full_name = models.CharField(max_length=255)
    ballot_number = models.IntegerField()
    candidate_id = models.IntegerField()
    candidate_active = models.BooleanField(default=False)
    stations = models.PositiveIntegerField(default=0)
    center_ids = ArrayField(models.IntegerField())
    station_numbers = ArrayField(models.PositiveSmallIntegerField(
        blank=True, null=True))
    stations_completed = models.PositiveIntegerField(default=0)
    votes = models.PositiveIntegerField(default=0)
    total_votes = models.PositiveIntegerField(default=0)
    all_candidate_votes = models.PositiveIntegerField(default=0)
    candidate_votes_included_quarantine = models.PositiveIntegerField(
        default=0)
    stations_complete_percent = models.IntegerField()


reversion.register(AllCandidatesVotes)
