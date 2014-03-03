from django.contrib.auth.models import User
from django.db import models
import reversion


class UserProfile(User):
    reset_password = models.BooleanField(default=True)

    class Meta:
        app_label = 'tally'

    def save(self, *args, **kwargs):
        """For the user to set their password if `reset_password` is True.
        """

        if self.reset_password:
            self.set_password(self.username)

        super(UserProfile, self).save(*args, **kwargs)

reversion.register(UserProfile)
