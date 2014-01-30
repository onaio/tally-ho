from django.db import models


class BaseModel(models.Model):
    class Meta:
        abstract = True

    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)
