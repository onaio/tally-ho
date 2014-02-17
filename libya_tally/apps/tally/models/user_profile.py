from django.contrib.auth.models import User
from django.db import models


class UserProfile(User):
    reset_password = models.BooleanField(default=True)

    class Meta:
        app_label = 'tally'
