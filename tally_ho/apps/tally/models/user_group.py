from django.db import models
from django.contrib.auth.models import Group
from tally_ho.apps.tally.models.tally import Tally
from django.db.models.signals import post_save
from django.dispatch import receiver
from tally_ho.libs.models.base_model import BaseModel


class UserGroup(BaseModel):
    group = models.OneToOneField(Group, on_delete=models.PROTECT)
    tally = models.ForeignKey(Tally,
                              null=True,
                              blank=True,
                              related_name='usergroup',
                              on_delete=models.PROTECT)
    idle_timeout = models.PositiveIntegerField(
        null=True, blank=True, default=60)


@receiver(post_save, sender=Group)
def create_user_group(sender, instance, created, **kwargs):
    if created:
        UserGroup.objects.create(group=instance)


@receiver(post_save, sender=Group)
def save_user_group(sender, instance, **kwargs):
    instance.usergroup.save()
