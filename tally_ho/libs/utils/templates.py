from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _


def getEditsLink(station):
    url_center = reverse('edit-centre', args=[station.center.tally.id,
                                              station.center.code])
    url_station = reverse('edit-station', args=[station.center.tally.id,
                                                station.center.code,
                                                station.station_number])

    template = '<a href="%s" class="btn btn-default btn-small vertical-margin">%s</a><a href="%s" class="btn btn-default btn-small vertical-margin">%s</a>'
    buttonHtml = template % (url_center, unicode(_('Center')),
                             url_station, unicode(_('Station')))

    return buttonHtml


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
        url = reverse('candidate-disable', args=[candidate.tally.id, candidate.id])
        buttonHtml = '<a href="%s">%s</a>' % (url,
                                              unicode(_('Disable Candidate')))
    elif not candidate.active:
        url = reverse('candidate-enable', args=[candidate.tally.id, candidate.id])
        buttonHtml = '<a href="%s">%s</a>' % (url,
                                              unicode(_('Enable Candidate')))

    return buttonHtml


def getEditUserLink(user, is_tally = False):
    if is_tally and user.tally:
        url = reverse('edit-user-tally', args=[user.tally.id, user.id])
    else:
        url = reverse('edit-user', args=[user.id])
    buttonHtml = '<a href="%s" class="btn btn-default btn-small">%s</a>' % (url, unicode(_('Edit')))

    return buttonHtml


def getTallyAdministerLink(tally):
    url = reverse('super-administrator', kwargs={'tally_id': tally.id})
    buttonHtml = '<a href="%s" class ="btn btn-default btn-small">%s</a>' %  \
                (url, unicode(_('Admin view')))

    return buttonHtml


def getTallyEditLink(tally):
    url = reverse('update-tally', kwargs={'tally_id': tally.id})
    buttonHtml = '<a href="%s" class ="btn btn-default btn-small">%s</a>' %  \
                (url, unicode(_('Edit tally')))

    return buttonHtml
