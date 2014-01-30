from django.db import models

from libya_tally.libs.models.base_model import BaseModel
from libya_tally.libs.models.enums.race_type import RaceType


class Candidate(BaseModel):
    race = models.OneToOneField('Race')
    sub_district = models.ManyToManyField('SubDistrict')

    candidate_id = models.PositiveIntegerField()
    duplicate = models.BooleanField()
    email = models.CharField()
    family_book_id = models.PositiveIntegerField()
    full_name = models.CharField()
    main_district_id = models.PositiveIntegerField()
    national_id = models.PositiveIntegerField()
    office_id = models.PositiveIntegerField()
    race_type = models.EnumField(RaceType)
    voting_district = models.PositiveIntegerField()
