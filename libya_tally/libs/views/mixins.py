import six
from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.core.urlresolvers import reverse

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

    def check_membership(self, group):
        """ Check required group(s) """
        # super admin skips group check
        if group == groups.SUPER_ADMINISTRATOR:
            return True

        return group in self.request.user.groups.values_list(
            "name", flat=True)

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
