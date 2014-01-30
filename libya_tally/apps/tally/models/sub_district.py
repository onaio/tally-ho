from django.db import models

from libya_tally.libs.models.base_model import BaseModel


class SubDistrict(BaseModel):
    name_ar = models.CharField()
    name_en = models.CharField()
