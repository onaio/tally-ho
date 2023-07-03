import reversion
from django.db import models
from enumfields import EnumIntegerField
import os

from django.dispatch import receiver

from tally_ho.libs.models.base_model import BaseModel
from tally_ho.libs.models.enums.disable_reason import DisableReason
from tally_ho.libs.utils.templates import get_electrol_race_link
from tally_ho.apps.tally.models.tally import Tally

def bck_grnd_img_directory_path(instance, filename):
    # file will be uploaded to
    # MEDIA_ROOT/<election_level>_<ballot_name>/
    # <tally_id>/<instance_id>/<filename>
    return str(
        f'{instance.election_level}_{instance.ballot_name}/'
        f'{instance.tally.id}/{instance.id}/{filename}'
    )


class ElectrolRace(BaseModel):
    class Meta:
        app_label = 'tally'
        ordering = ['ballot_name']
        unique_together = (('election_level', 'ballot_name', 'tally'))
    election_level = models.CharField(max_length=256, null=True)
    ballot_name = models.CharField(max_length=256, null=True)
    active = models.BooleanField(default=True)
    disable_reason = EnumIntegerField(DisableReason, null=True, default=None)
    tally = models.ForeignKey(Tally,
                              null=True,
                              blank=True,
                              related_name='electrol_races',
                              on_delete=models.PROTECT)
    background_image = models.FileField(upload_to=bck_grnd_img_directory_path,
                                        null=True,
                                        blank=True,
                                        default="")

    def __str__(self):
        return u'%s - %s' % (self.election_level, self.ballot_name)

    @property
    def get_action_button(self):
        return get_electrol_race_link(self) if self else None

@receiver(
        models.signals.pre_save,
        sender=ElectrolRace,
        dispatch_uid="electrol_race_update")
def auto_delete_background_image(sender, instance, **kwargs):
    """
    Deletes old background_image from filesystem
    when corresponding `background_image` property value is updated
    with new background_image.
    """
    if not instance.pk:
        return False

    try:
        old_background_image =\
            sender.objects.get(pk=instance.pk).background_image
    except sender.DoesNotExist:
        return False

    new_background_image = instance.background_image
    if old_background_image and old_background_image != new_background_image:
        os.remove(old_background_image.path)
    return False


reversion.register(ElectrolRace)
