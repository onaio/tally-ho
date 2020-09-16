from django import template

from tally_ho.apps.tally.models.tally import Tally

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
    minutes = divmod(total_time_in_seconds, one_minute_in_seconds)[0]
    hours = divmod(minutes, one_minute_in_seconds)[0]
    forms_processed_per_hour = None

    if round(hours):
        forms_processed_per_hour = total_forms_processed/float(hours)

    return forms_processed_per_hour\
        if forms_processed_per_hour else total_forms_processed


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
