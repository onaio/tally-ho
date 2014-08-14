from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _


def getEditCenterLink(station):
    url = reverse('edit-centre', args=[station.center.code])
    buttonHtml = '<a href="%s" class="btn btn-default btn-small">%s</a>' % (url, unicode(_('Edit Center')))

    return buttonHtml


def getEditStationLink(station):
    url = reverse('edit-station', args=[station.center.code,
                                        station.station_number])
    buttonHtml = '<a href="%s" class="btn btn-default btn-small">%s</a>' % (url, unicode(_('Edit Station')))

    return buttonHtml
