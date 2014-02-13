import six
from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.core.urlresolvers import reverse
from django.http import HttpResponseBadRequest
from django.utils.translation import ugettext as _
from eztables.forms import DatatablesForm

from libya_tally.libs.permissions import groups


# from django-braces
class GroupRequiredMixin(object):
    group_required = None

    def get_group_required(self):
        required_types = (list, tuple) + six.string_types
        if self.group_required is None \
                or (not isinstance(self.group_required, required_types)):

            raise ImproperlyConfigured(
                "'GroupRequiredMixin' requires "
                "'group_required' attribute to be set and be one of the "
                "following types: string, unicode, list, or tuple.")
        return self.group_required

    def check_membership(self, allowed_groups):
        """ Check required group(s) """
        # super admin skips group check
        user_groups = self.request.user.groups.values_list("name", flat=True)

        if groups.SUPER_ADMINISTRATOR in user_groups:
            return True

        if not isinstance(allowed_groups, list):
            allowed_groups = [allowed_groups]

        for group in allowed_groups:
            if group in user_groups:
                return True

        return False

    def dispatch(self, request, *args, **kwargs):
        self.request = request
        in_group = False
        if self.request.user.is_authenticated():
            in_group = self.check_membership(self.get_group_required())

        if not in_group:
            raise PermissionDenied
        return super(GroupRequiredMixin, self).dispatch(
            request, *args, **kwargs)


class ReverseSuccessURLMixin(object):
    def get_success_url(self):
        if self.success_url:
            self.success_url = reverse(self.success_url)
        return super(ReverseSuccessURLMixin, self).get_success_url()


class DatatablesDisplayFieldsMixin(object):
    display_fields = None

    def get_row(self, row):
        '''Format a single row (if necessary)'''

        if self.display_fields is None:
            raise ImproperlyConfigured(_(
                u"`DatatablesDisplayMixin` requires a displa_fields tuple to"
                " be defined."))

        data = {}
        for field, name in self.display_fields:
            data[field] = getattr(row, name)
        return [data[field] for field in self.fields]

    def process_dt_response(self, data):
        self.form = DatatablesForm(data)

        if self.form.is_valid():
            self.object_list = self.get_queryset()

            return self.render_to_response(self.form)
        else:
            return HttpResponseBadRequest()
