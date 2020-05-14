from django import template

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
