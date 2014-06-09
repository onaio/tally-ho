from django.core.urlresolvers import reverse

def getActiveCenterLink(station):
  buttonHtml = 'Center Disabled'
  if station.center.active == 1:
    url = reverse('disable', args=[station.center.code])
    buttonHtml = '<a href="%s">Disable Center</a>' % url

  return buttonHtml

def getActiveStationLink(station):
  buttonHtml = 'Station Disabled'
  if station.active == 1:
    url = reverse('disable', args=[station.center.code, station.station_number])
    buttonHtml = '<a href="%s">Disable Station</a>' % url

  return buttonHtml
