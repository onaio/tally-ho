from django.conf import settings
from django.contrib.sites.models import Site


def site_name(request):
    site_id = getattr(settings, 'SITE_ID', None)
    try:
        site = Site.objects.get(pk=site_id)
    except Site.DoesNotExist:
        site_name = 'example.org'
    else:
        site_name = site.name
    return {'SITE_NAME': site_name}


def locale(request):
    locale = 'en'

    if hasattr(request, 'session'):
        locale = request.session.get('locale')

        if not locale:
            locale = 'ar'

        request.session.get('locale')
        request.session['django_language'] = locale

    return {'locale': locale}
