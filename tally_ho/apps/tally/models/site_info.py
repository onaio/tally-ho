from django.db import models
from django.contrib.sites.models import Site
from django.db.models.signals import post_save
from django.dispatch import receiver
from tally_ho.libs.models.base_model import BaseModel


class SiteInfo(BaseModel):
    site = models.OneToOneField(Site, on_delete=models.PROTECT)
    idle_timeout = models.PositiveIntegerField(
        null=True, blank=True, default=60)

    def __str__(self):
        return u'%s - %s' % (self.site.name, self.idle_timeout)


@receiver(post_save, sender=Site)
def create_site_info(sender, instance, created, **kwargs):
    if created:
        SiteInfo.objects.create(group=instance)


@receiver(post_save, sender=Site)
def save_site_info(sender, instance, **kwargs):
    instance.siteinfo.save()
