import six

from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.urls import reverse

from tally_ho.libs.utils.collections import listify
from tally_ho.libs.permissions import groups


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

        return groups.SUPER_ADMINISTRATOR in user_groups or\
            set(listify(allowed_groups)) & set(user_groups)

    def dispatch(self, request, *args, **kwargs):
        self.request = request

        if not (self.request.user.is_authenticated and
                self.check_membership(self.get_group_required())):
            raise PermissionDenied

        return super(GroupRequiredMixin, self).dispatch(
            request, *args, **kwargs)


class ReverseSuccessURLMixin(object):
    def get_success_url(self):
        if self.success_url:
            self.success_url = reverse(self.success_url)

        return super(ReverseSuccessURLMixin, self).get_success_url()
