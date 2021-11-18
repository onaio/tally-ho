from django.contrib.postgres.aggregates.general import ArrayAgg
from django.db import transaction, connection
from django.db.models import ExpressionWrapper, Count, Q, F, FloatField,\
    Func, Subquery, OuterRef, Case, IntegerField, When, Value as V

from tally_ho import celery_tally_ho
from tally_ho.apps.tally.models.result import Result
from tally_ho.apps.tally.models.candidate import Candidate
from tally_ho.libs.models.enums.entry_version import EntryVersion
from tally_ho.libs.models.enums.form_state import FormState

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


def build_tally_candidates_votes_queryset():
    """
    Create a queryset for all candidates votes in a tally.

    returns: queryset of all candidates votes.
    """
    template = '%(function)s(%(expressions)s AS FLOAT)'
    stations_completed =\
        Func(F('stations_completed'), function='CAST', template=template)
    stations = Func(F('stations'), function='CAST', template=template)
    ew = Round((100 * stations_completed/stations), digits=3)

    candidate_votes_query =\
        Subquery(
            Result.objects.filter(
                candidate__tally__id=OuterRef('tally_id'),
                candidate__id=OuterRef('candidate_id'),
                entry_version=EntryVersion.FINAL,
                result_form__form_state=FormState.ARCHIVED,
                active=True).annotate(
                    candidate_votes=Case(
                        When(votes__isnull=False,
                             then=F('votes')),
                        default=V(0),
                        output_field=IntegerField())).values(
                            'candidate_votes'
                        )[:1], output_field=IntegerField())

    all_candidate_votes_query =\
        Subquery(
            Result.objects.filter(
                candidate__tally__id=OuterRef('tally_id'),
                candidate__id=OuterRef('candidate_id'),
                entry_version=EntryVersion.FINAL,
                active=True).filter(
                    Q(result_form__form_state=FormState.ARCHIVED) |
                    Q(result_form__form_state=FormState.AUDIT)
            ).annotate(
                    candidate_votes=Case(
                        When(votes__isnull=False,
                             then=F('votes')),
                        default=V(0),
                        output_field=IntegerField())).values(
                            'candidate_votes'
            )[:1], output_field=IntegerField())

    qs = Candidate.objects.all()\
        .values('full_name')\
        .annotate(
            tally_id=F('tally__id'),
            candidate_id=F('id'),
            ballot_number=F('ballot__number'),
            candidate_active=F('active'),
            stations=Count(
                'ballot__resultform',
                filter=Q(ballot__resultform__tally__id=F('tally_id'),
                         ballot__resultform__center__isnull=False,
                         ballot__resultform__station_number__isnull=False,
                         ballot__resultform__ballot__isnull=False)
            ),
            stations_completed=Count(
                'ballot__resultform',
                filter=Q(
                    ballot__resultform__tally__id=F('tally_id'),
                    ballot__resultform__center__isnull=False,
                    ballot__resultform__station_number__isnull=False,
                    ballot__resultform__ballot__isnull=False,
                    ballot__resultform__form_state=FormState.ARCHIVED)
            ),
            votes=candidate_votes_query,
            total_votes=Case(
                When(
                    votes__isnull=False,
                    then=F('votes')
                ),
                default=V(0),
                output_field=IntegerField()
            ),
            all_candidate_votes=all_candidate_votes_query,
            candidate_votes_included_quarantine=Case(
                When(
                    all_candidate_votes__isnull=False,
                    then=F('all_candidate_votes')
                ),
                default=V(0),
                output_field=IntegerField()
            ),
            stations_complete_percent=Case(
                When(stations__gt=0, then=ew),
                default=V(0),
                output_field=FloatField()
            ),
            center_ids=ArrayAgg(
                'ballot__resultform__center__id',
                distinct=True),
            station_numbers=ArrayAgg(
                'ballot__resultform__station_number',
                distinct=True))

    return qs

@transaction.atomic
def refresh_all_candidates_votes_materiliazed_view():
    with connection.cursor() as cursor:
        cursor.execute(
            "REFRESH MATERIALIZED VIEW CONCURRENTLY tally_allcandidatesvotes")

@celery_tally_ho.task
def async_refresh_all_candidates_votes_materiliazed_view():
    return refresh_all_candidates_votes_materiliazed_view()
