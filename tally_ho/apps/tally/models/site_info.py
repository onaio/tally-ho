from django.contrib.sites.models import Site
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from tally_ho.libs.models.base_model import BaseModel


class SiteInfo(BaseModel):
    site = models.OneToOneField(Site, on_delete=models.PROTECT)
    user_idle_timeout = models.PositiveIntegerField(default=60)

    def __str__(self):
        return '%s - %s' % (self.site.name, self.user_idle_timeout)


@receiver(post_save, sender=Site)
def create_site_info(sender, instance, created, **kwargs):
    if created:
        SiteInfo.objects.create(site=instance)


@receiver(post_save, sender=Site)
def update_site_info(sender, instance, **kwargs):
    instance.siteinfo.save()
