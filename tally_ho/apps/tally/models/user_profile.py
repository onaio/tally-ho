import reversion

from django.contrib.auth.models import User
from django.db import models

from tally_ho.apps.tally.models.tally import Tally
from tally_ho.libs.permissions import groups
from tally_ho.libs.utils.templates import get_edit_user_link


class UserProfile(User):
    reset_password = models.BooleanField(default=True)
    administrated_tallies = models.ManyToManyField(
        Tally,
        blank=True,
        default=None,
        related_name='administrators')
    tally = models.ForeignKey(Tally,
                              blank=True,
                              null=True,
                              related_name='users',
                              on_delete=models.PROTECT)

    class Meta:
        app_label = 'tally'

    def save(self, *args, **kwargs):
        """For the user to set their password if `reset_password` is True.
        """

        if self.reset_password:
            self.set_password(self.username)

        super(UserProfile, self).save(*args, **kwargs)

    @property
    def get_edit_link(self):
        return get_edit_user_link(self) if self else None

    @property
    def get_edit_tally_link(self):
        return get_edit_user_link(self, True) if self else None

    @property
    def is_administrator(self):
        return groups.SUPER_ADMINISTRATOR in self.groups.values_list(
            'name', flat=True)

    def __str__(self):
        return '%s - %s %s' % (self.username, self.first_name, self.last_name)


reversion.register(UserProfile)
