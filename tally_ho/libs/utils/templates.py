from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _


def getActiveCenterLink(station):
    buttonHtml = 'Center disabled'
    if station.center.active:
        url = reverse('disable', args=[station.center.code])
        buttonHtml = '<a href="%s">%s</a>' % (url,
                                              unicode(_('Disable Center')))
    else:
        url = reverse('enable', args=[station.center.code])
        buttonHtml = '<a href="%s">%s</a>' % (url, unicode(_('Enable Center')))

    return buttonHtml


def getActiveStationLink(station):
    buttonHtml = 'Station disabled'
    if station.active:
        url = reverse('disable', args=[station.center.code,
                                       station.station_number])
        buttonHtml = '<a href="%s">%s</a>' % (url,
                                              unicode(_('Disable Station')))
    elif station.center.active:
        url = reverse('enable', args=[station.center.code,
                                      station.station_number])
        buttonHtml = '<a href="%s">%s</a>' % (url,
                                              unicode(_('Enable Station')))

    return buttonHtml


def getActiveCandidateLink(candidate):
    buttonHtml = 'Candidate disabled'
    if candidate.active:
        url = reverse('candidate-disable', args=[candidate.candidate_id])
        buttonHtml = '<a href="%s">%s</a>' % (url,
                                              unicode(_('Disable Candidate')))
    elif not candidate.active:
        url = reverse('candidate-enable', args=[candidate.candidate_id])
        buttonHtml = '<a href="%s">%s</a>' % (url,
                                              unicode(_('Enable Candidate')))

    return buttonHtml
