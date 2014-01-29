from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

from tally.apps.main.views.home_view import HomeView


urlpatterns = patterns(
    '',
    url(r'^$', HomeView.as_view(), name='home'),

    url(r'^admin/', include(admin.site.urls)),
)
