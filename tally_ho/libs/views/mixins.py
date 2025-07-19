import json

from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse

from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.apps.tally.models.tally import Tally
from tally_ho.apps.tally.models.user_profile import UserProfile
from tally_ho.libs.permissions import groups
from tally_ho.libs.utils.collections import listify
from tally_ho.libs.utils.context_processors import (
    get_datatables_language_de_from_locale, get_deployed_site_url)

admin_groups = set((groups.TALLY_MANAGER, groups.SUPER_ADMINISTRATOR))


def check_membership(allowed_groups, user):
    """Check required group(s).

    Verify that the user is in a permitted group, always returns True if
    the user is a Super Administrator.

    :param allowed_groups: The groups permitted.

    :returns: True if user is in an allowed group, otherwise False.
    """
    user_groups = set(groups.user_groups(user))

    # super admin skips group check
    return admin_groups & user_groups or\
        set(listify(allowed_groups)) & user_groups


# from django-braces
class GroupRequiredMixin(object):
    group_required = None

    def get_group_required(self):
        required_types = (list, tuple, str)

        if self.group_required is None or not isinstance(
                self.group_required, required_types):
            raise ImproperlyConfigured(
                "'GroupRequiredMixin' requires "
                "'group_required' attribute to be set and be one of the "
                "following types: string, unicode, list, or tuple.")

        return self.group_required

    def dispatch(self, request, *args, **kwargs):
        self.request = request

        if not (self.request.user.is_authenticated and check_membership(
                self.get_group_required(), self.request.user)):
            raise PermissionDenied

        return super(GroupRequiredMixin, self).dispatch(
            request, *args, **kwargs)


class ReverseSuccessURLMixin(object):
    def get_success_url(self):
        if self.success_url:
            if hasattr(self, 'tally_id'):
                self.success_url = reverse(self.success_url,
                                           kwargs={'tally_id': self.tally_id})
            else:
                self.success_url = reverse(self.success_url)

        return super(ReverseSuccessURLMixin, self).get_success_url()


class PrintedResultFormMixin(object):
    def render_to_response(self, context, **response_kwargs):
        del context['view']
        return HttpResponse(
            json.dumps(context),
            content_type='application/json',
            **response_kwargs
        )

    def get(self, *args, **kwargs):
        result_form_pk = kwargs.get('resultFormPk')

        status = 'ok'
        try:
            result_form = ResultForm.objects.get(pk=result_form_pk)
            self.set_printed(result_form)
        except ResultForm.DoesNotExist:
            status = 'error'

        return self.render_to_response(self.get_context_data(status=status))

    def set_printed(self, result_form):
        pass


class TallyAccessMixin(object):
    def has_tally_access(self, userprofile, tally):
        user_groups = groups.user_groups(userprofile)

        has_access = False
        if groups.TALLY_MANAGER in user_groups:
            has_access = True

        elif groups.SUPER_ADMINISTRATOR in user_groups and \
                userprofile.administrated_tallies.filter(id=tally.id):
            has_access = True

        elif userprofile.tally == tally:
            has_access = True

        return has_access

    def dispatch(self, request, *args, **kwargs):
        self.request = request
        tally_id = kwargs.get('tally_id')

        tally = get_object_or_404(Tally, id=tally_id)
        user_profile = UserProfile.objects.get(id=self.request.user.id)

        if not (self.has_tally_access(user_profile, tally)):
            raise PermissionDenied

        return super(TallyAccessMixin, self).dispatch(request, *args, **kwargs)


class DataTablesMixin(object):
    """
    Mixin that provides standard DataTables context variables.
    Includes all static variables used by data/table.html template.
    """

    def get_context_data(self, **kwargs):
        context = super(DataTablesMixin, self).get_context_data(**kwargs)

        # Static variables (same across all views)
        context.update({
            'languageDE': get_datatables_language_de_from_locale(self.request),
            'deployedSiteUrl': get_deployed_site_url(),
            'enable_responsive': False,
            'enable_scroll_x': True,
            'regions_list_download_url': '/ajax/download-regions-list/',
            'offices_list_download_url': '/ajax/download-offices-list/',
            'get_centers_stations_url': '/ajax/get-centers-stations/',
            'get_export_url': '/ajax/get-export/',
            'results_download_url': '/ajax/download-results/',
            'centers_by_mun_results_download_url':
                '/ajax/download-centers-by-mun-results/',
            'centers_by_mun_candidate_votes_results_download_url':
                '/ajax/download-centers-by-mun-results-candidates-votes/',
            'centers_stations_by_mun_candidates_votes_results_download_url':
                '/ajax/download-centers-stations-by-mun-results-candidates-votes/',
            'sub_cons_list_download_url': '/ajax/download-sub-cons-list/',
            'result_forms_download_url': '/ajax/download-result-forms/',
            'centers_and_stations_list_download_url':
                '/ajax/download-centers-and-stations-list/',
            'candidates_list_download_url': '/ajax/download-candidates-list/',
        })

        return context
