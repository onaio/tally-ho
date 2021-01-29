from django.db import models
import reversion


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
    center_id = models.IntegerField()
    center_code = models.IntegerField()
    station_number = models.IntegerField()
    station_id = models.IntegerField()
    stations_completed = models.PositiveIntegerField(default=0)
    votes = models.PositiveIntegerField(default=0)
    total_votes = models.PositiveIntegerField(default=0)
    all_candidate_votes = models.PositiveIntegerField(default=0)
    candidate_votes_included_quarantine = models.PositiveIntegerField(
        default=0)
    stations_complete_percent = models.IntegerField()


reversion.register(AllCandidatesVotes)
