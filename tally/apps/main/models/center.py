import revision

from tally.libs.models.base_model import BaseModel


class Center(BaseModel):

    code = models.IntegerField(unique=True)
    latitude = models.FloatField()
    longitutde = models.FloatField()
    female_registrants = models.IntegerField()
    mahalla = models.CharField()
    male_registrants = models.IntegerField()
    name = models.CharField(unique=True)
    number = models.IntegerField(unique=True)
    region = models.CharField()
    center_type = models.TextField()
    village = models.CharField()


revision.register(Centre)
