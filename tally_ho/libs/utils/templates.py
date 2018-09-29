from django.urls import reverse
from django.utils.translation import ugettext_lazy as _


def get_edits_link(station):
    url_center = reverse('edit-center', args=[station.center.tally.id,
                                              station.center.code])
    url_station = reverse('edit-station', args=[station.center.tally.id,
                                                station.center.code,
                                                station.station_number])

    template = (
        '<a href="%s" class="btn btn-default btn-small vertical-margin">%s'
        '</a><a href="%s" class="btn btn-default btn-small vertical-margin">%s'
        '</a>'
    )
    button_html = template % (url_center, _('Center'),
                              url_station, _('Station'))

    return button_html


def get_active_center_link(station):
    button_html = 'Center disabled'
    if station.center.active:
        url = reverse('disable', args=[station.center.code])
        button_html = '<a href="%s">%s</a>' % (
            url, _('Disable Center'))
    else:
        url = reverse('enable', args=[station.center.code])
        button_html = '<a href="%s">%s</a>' % (url, _('Enable Center'))

    return button_html


def get_active_station_link(station):
    button_html = 'Station disabled'
    if station.active:
        url = reverse('disable', args=[station.center.code,
                                       station.station_number])
        button_html = '<a href="%s">%s</a>' % (
            url, _('Disable Station'))
    elif station.center.active:
        url = reverse('enable', args=[station.center.code,
                                      station.station_number])
        button_html = '<a href="%s">%s</a>' % (
            url, _('Enable Station'))

    return button_html


def get_active_candidate_link(candidate):

    if candidate.active:
        url = reverse('candidate-disable',
                      args=[candidate.tally.id, candidate.id])
        text = 'Disable'
    else:
        url = reverse('candidate-enable',
                      args=[candidate.tally.id, candidate.id])
        text = 'Enable'

    button_html = '<a href="%s" class="btn btn-default btn-small">%s</a>' %\
        (url, _(text))

    return button_html


def get_edit_user_link(user, is_tally=False):
    if is_tally and user.tally:
        url = reverse('edit-user-tally', args=[user.tally.id, user.id])
    else:
        url = reverse('edit-user', args=[user.id])
    button_html = '<a href="%s" class="btn btn-default btn-small">%s</a>' %\
        (url, _('Edit'))

    return button_html


def get_tally_administer_link(tally):
    url = reverse('super-administrator', kwargs={'tally_id': tally.id})
    button_html = '<a href="%s" class ="btn btn-default btn-small">%s</a>' %\
        (url, _('Admin View'))

    return button_html


def get_tally_edit_link(tally):
    url = reverse('update-tally', kwargs={'tally_id': tally.id})
    button_html = '<a href="%s" class ="btn btn-default btn-small">%s</a>' %\
        (url, _('Edit'))

    return button_html
