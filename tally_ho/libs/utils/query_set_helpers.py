from django.db.models import ExpressionWrapper, FloatField, Func


class Cast(Func):
    function = 'CAST'
    template = '%(function)s(%(expressions)s AS %(db_type)s)'

    def __init__(self, expression, db_type):
        # convert second positional argument to kwarg to be used in
        # function template
        super(Cast, self).__init__(expression, db_type=db_type)


def Round(expr, digits=0, output_field=FloatField()):
    # converting to numeric is necessary for postgres
    return ExpressionWrapper(
      Func(Cast(expr, 'numeric'),
           digits,
           function='ROUND'), output_field=output_field)
