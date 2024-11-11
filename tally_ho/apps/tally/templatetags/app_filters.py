from django import template

from tally_ho.apps.tally.models.tally import Tally
from tally_ho.libs.models.enums.actions_prior import ActionsPrior
from tally_ho.libs.models.enums.audit_resolution import AuditResolution

register = template.Library()


@register.filter(name="forms_processed_per_hour")
def forms_processed_per_hour(total_forms_processed, total_time_in_seconds):
    """Calculate forms processed per hour.

    Divide total forms processed by the total time it took to process
    all the forms.
    :param total_forms_processed: Total number of forms processed.
    :param total_time_in_seconds: Total time for processing all forms.

    :returns: An Integer of forms processed per hour.
    """
    one_minute_in_seconds = 60
    one_hour_in_minutes = 60
    one_hour_in_seconds = one_minute_in_seconds * one_hour_in_minutes
    hours = (total_time_in_seconds / one_hour_in_seconds)
    processed_forms_per_hour = total_forms_processed
    if hours > 1:
        processed_forms_per_hour = round(total_forms_processed / hours, 2)
    return processed_forms_per_hour

@register.filter(name="get_tally_name")
def get_tally_name(tally_id):
    """Get tally name.

    :param tally_id: Id to be used to retrieve a tally

    :returns: Tally name as a String.
    """
    tally_name = None

    try:
        tally = Tally.objects.get(id=tally_id)
        tally_name = tally.name
    except Tally.DoesNotExist:
        pass

    return tally_name

def get_action_prior_label_by_number(choice_number):
    for number, choice_label in ActionsPrior.choices():
        if number == choice_number:
            return choice_label

@register.filter(name="get_audit_action_name")
def get_audit_action_name(action_prior_enum):
    """Get audit action name.

    :param action_prior_enum: Audit prior enum

    :returns: Action prior name as a String.
    """
    return get_action_prior_label_by_number(action_prior_enum.value)

def get_audti_resolution_label_by_number(choice_number):
    for number, choice_label in AuditResolution.choices():
        if number == choice_number:
            return choice_label

@register.filter(name="get_audit_resolution_name")
def get_audit_resolution_name(audit_resolution_enum):
    """Get audit resolution name.

    :param audit_resolution_enum: Audit resolution enum

    :returns: Audit resolution name as a String.
    """
    return get_audti_resolution_label_by_number(audit_resolution_enum.value)
