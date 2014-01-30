from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

from libya_tally.apps.tally.views.home import HomeView


urlpatterns = patterns(
    '',
    url(r'^$', HomeView.as_view(), name='home'),

    url(r'^admin/', include(admin.site.urls)),
)
