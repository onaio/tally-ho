import copy
import six
import json

from django.db.models import Q
from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.core.urlresolvers import reverse
from django.http import HttpResponseBadRequest, HttpResponse
from django.shortcuts import get_object_or_404
from eztables.forms import DatatablesForm
from operator import or_

from tally_ho.libs.utils.collections import listify
from tally_ho.libs.permissions import groups
from tally_ho.apps.tally.models.result_form import ResultForm
from tally_ho.apps.tally.models.user_profile import UserProfile
from tally_ho.apps.tally.models.tally import Tally


# from django-braces
class GroupRequiredMixin(object):
    group_required = None

    def get_group_required(self):
        required_types = (list, tuple) + six.string_types

        if self.group_required is None or not isinstance(
                self.group_required, required_types):
            raise ImproperlyConfigured(
                "'GroupRequiredMixin' requires "
                "'group_required' attribute to be set and be one of the "
                "following types: string, unicode, list, or tuple.")

        return self.group_required

    def check_membership(self, allowed_groups):
        """Check required group(s).

        Verify that the user is in a permitted group, always returns True if
        the user is a Super Administrator.

        :param allowed_groups: The groups permitted.

        :returns: True if user is in an allowed group, otherwise False.
        """
        # super admin skips group check
        user_groups = groups.user_groups(self.request.user)

        if len(listify(allowed_groups)) == 1 and \
                groups.TALLY_MANAGER in listify(allowed_groups):
            return groups.TALLY_MANAGER in user_groups;

        else:
            return groups.TALLY_MANAGER in user_groups or\
                    groups.SUPER_ADMINISTRATOR in user_groups or\
                    set(listify(allowed_groups)) & set(user_groups)

    def dispatch(self, request, *args, **kwargs):
        self.request = request

        if not (self.request.user.is_authenticated() and
                self.check_membership(self.get_group_required())):
            raise PermissionDenied

        return super(GroupRequiredMixin, self).dispatch(
            request, *args, **kwargs)


class ReverseSuccessURLMixin(object):
    def get_success_url(self):
        if self.success_url:
            if hasattr(self, 'tally_id'):
                self.success_url = reverse(self.success_url, kwargs={'tally_id': self.tally_id})
            else:
                self.success_url = reverse(self.success_url)

        return super(ReverseSuccessURLMixin, self).get_success_url()


class DatatablesDisplayFieldsMixin(object):
    display_fields = None

    def get_row(self, row):
        """Format a single row if necessary.

        :param row: The row to format.

        :raises: `ImproperlyConfigured` exception is class does not have a
            display_fields member.

        :returns: A list of data.
        """
        if self.display_fields is None:
            raise ImproperlyConfigured(
                u"`DatatablesDisplayMixin` requires a display_fields tuple to"
                " be defined.")

        return [getattr(row, name) for field, name in self.display_fields if
                field in self.fields]

    def process_dt_response(self, data):
        self.form = DatatablesForm(data)

        if self.form.is_valid():
            self.object_list = self.get_queryset()

            return self.render_to_response(self.form)
        else:
            return HttpResponseBadRequest()

    def global_search(self, queryset, excludes=None):
        """Filter a queryset using a global search.

        :param queryset: The queryset to filter.

        :returns: A filtered queryset.
        """
        qs = copy.deepcopy(queryset)
        qs2 = copy.deepcopy(queryset)
        zero_start_term = False
        search = search_str = self.dt_data['sSearch']
        fields = self.get_db_fields()

        if excludes:
            for exclude in excludes:
                fields.remove(exclude) if exclude in fields else None

        if search:
            if self.dt_data['bRegex']:
                criterions = [Q(**{'%s__iregex' % field: search})
                              for field in fields
                              if self.can_regex(field)]

                if len(criterions) > 0:
                    search = reduce(or_, criterions)
                    queryset = queryset.filter(search)
            else:
                for term in search.split():
                    if term.startswith(u'0'):
                        zero_start_term = True

                    criterions = (Q(**{'%s__icontains' % field: term})
                                  for field in fields)
                    search = reduce(or_, criterions)
                    queryset = queryset.filter(search)

            if zero_start_term:
                for term in search_str.split():
                    try:
                        term = int(term)
                    except ValueError:
                        pass
                    else:
                        criterions = (Q(**{'%s__istartswith' % field: term})
                                      for field in fields)
                        search = reduce(or_, criterions)
                        qs = qs.filter(search)

                queryset = qs2.filter(Q(pk__in=qs.values('pk'))
                                      | Q(pk__in=queryset.values('pk')))

        return queryset


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
            result_form = ResultForm.objects.get(pk=result_form_pk);
            self.set_printed(result_form)
        except ResultForm.DoesNotExist:
            status = 'error'

        return self.render_to_response(self.get_context_data(status = status))

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

        if not(self.has_tally_access(user_profile, tally)):
            raise PermissionDenied

        return super(TallyAccessMixin, self).dispatch(request, *args, **kwargs)
