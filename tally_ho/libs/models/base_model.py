from django.db import models
from django.utils import timezone


class BaseModel(models.Model):
    class Meta:
        abstract = True

    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    @property
    def modified_date_formatted(self):
        # Convert UTC datetime to the configured timezone
        local_dt = timezone.localtime(self.modified_date)
        return local_dt.strftime('%a, %d %b %Y %H:%M:%S %Z')

    def reload(self):
        new_self = self.__class__.objects.get(pk=self.pk)
        # Clear and update the old dict.
        self.__dict__.clear()
        self.__dict__.update(new_self.__dict__)
