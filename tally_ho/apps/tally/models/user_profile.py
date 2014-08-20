import reversion

from django.contrib.auth.models import User
from django.db import models

from tally_ho.apps.tally.models.tally import Tally


class UserProfile(User):
    reset_password = models.BooleanField(default=True)
    administrated_tallies = models.ManyToManyField(Tally, blank=True, null=True, default=None, related_name='administrators')
    tally = models.ForeignKey(Tally, blank=True, null=True, related_name='users')

    class Meta:
        app_label = 'tally'

    def save(self, *args, **kwargs):
        """For the user to set their password if `reset_password` is True.
        """

        if self.reset_password:
            self.set_password(self.username)

        super(UserProfile, self).save(*args, **kwargs)

    def __unicode__(self):
        return '%s - %s %s' % (self.username, self.first_name, self.last_name)

reversion.register(UserProfile)
